from django.shortcuts import render, render_to_response
import os, time, math, itertools, csv, random
from itertools import chain

# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import loader, RequestContext
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test


from .models import *

def super_check(user):
    return user.groups.filter(name__in=['superuser'])


@login_required
def switch_mode(request):

    if request.session['appmode']=='scoping':
        request.session['appmode']='snoballing'
        return HttpResponseRedirect(reverse('scoping:snowball'))
    else:
        request.session['appmode']='scoping'
        return HttpResponseRedirect(reverse('scoping:index'))



########################################################
## Homepage - list the queries, form for adding new ones

@login_required
def index(request):

    if request.session.get('appmode', None) == None: 
        request.session['appmode']='scoping'
#        request.session['scoping']=True

    print("Session variable (appmode): "+str(request.session['appmode']))

    template = loader.get_template('scoping/index.html')

    queries_none  = Query.objects.all().filter(type=None)
    queries_dft   = Query.objects.all().filter(type="default")
    queries       = queries_none | queries_dft
    queries       = queries.order_by('-id')
    query         = queries.last()
    users         = User.objects.all()
    technologies  = Technology.objects.all()

    for q in queries:
        q.tech = q.technology
        if q.technology==None:
            q.tech="None"
        else:
            q.tech=q.technology.name
        #print(q.tech)

    context = {
      
      'queries'      : queries,
      'query'        : query,
      'users'        : users,
      'active_users' : users.filter(username=request.user.username),
      'techs'        : technologies,
      'appmode'      : request.session['appmode']
    }

    return HttpResponse(template.render(context, request))

########################################################
## Tech Homepage - list the technologies, form for adding new ones

@login_required
def technologies(request):

    template = loader.get_template('scoping/tech.html')

    technologies = Technology.objects.all()

    users = User.objects.all()

    for t in technologies:
        t.queries = len(t.query_set.all())
        tdocs = Doc.objects.filter(technology=t)
        itdocs = Doc.objects.filter(query__technology=t)
        tdocs = tdocs | itdocs
        t.docs = tdocs.distinct().count()

    context = {
      'techs'    : technologies,
      'users'    : users
    }

    return HttpResponse(template.render(context, request))

########################################################
## edit tech query

@login_required
def technology_query(request):

    tid = request.GET.get('tid', None)
    qid = request.GET.get('qid', None)

    q = Query.objects.get(pk=qid)
    if tid=="None":
        q.technology = None
    else:
        t = Technology.objects.get(pk=tid)
        q.technology = t

    q.save()

    return HttpResponse("")

########################################################
## Snowballing homepage
@login_required
def snowball(request):
    template        = loader.get_template('scoping/snowball.html')

    sb_sessions     = SnowballingSession.objects.all().order_by('-id')
    # Get latest step associated with each SB sessions
    sb_session_last = sb_sessions.last()
    sb_info = [] 
    for sbs in sb_sessions:
        sb_info_tmp = {}
        sb_info_tmp['id']     = sbs.id
        sb_info_tmp['name']   = sbs.name
        sb_info_tmp['ip']     = sbs.initial_pearls
        sb_info_tmp['date']   = sbs.date
        sb_info_tmp['status'] = sbs.status
        sb_qs = Query.objects.filter(snowball = sbs.id)
        step  = "1"
        nbdocsel = 0
        nbdoctot = 0
        nbdocrev = 0
        for q in sb_qs:
            s = q.title.split("_")[2]
            if s > step:
                step = s
            nbdocsel += DocOwnership.objects.filter(query = q, relevant = 1).count()
            nbdoctot += DocOwnership.objects.filter(query = q).count()
            nbdocrev += DocOwnership.objects.filter(query = q, relevant = 0).count()
        sb_info_tmp['ns'] = step
        sb_info_tmp['lq'] = sb_qs.last().id 
        sb_info_tmp['rc'] = sb_qs.last().r_count 
        sb_info_tmp['ndsel'] = str(nbdocsel)
        sb_info_tmp['ndtot'] = str(nbdoctot)
        sb_info_tmp['ndrev'] = str(nbdocrev)
         
        sb_info.append(sb_info_tmp)

    context = {
        'sb_sessions'    : sb_sessions,
        'sb_session_last': sb_session_last,
        'sb_info'        : sb_info
    }
    return HttpResponse(template.render(context, request))

#########################################################
## Test the SSH connection
def ssh_test():

    NoSSHTest = False 

    if NoSSHTest :
      ssh_working = True
    else :
      ssh_working = subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/check_selenium_ip.py", "-b", "chrome"], stdout=subprocess.PIPE).communicate()[0].strip().decode()
      print(repr(ssh_working))
    if ssh_working == "False":
        subprocess.Popen(["setsid","ssh","-D","1080","minx@aix.pik-potsdam.de"])
    return(ssh_working)

########################################################
## Add the technology
@login_required
def add_tech(request):
    tname = request.POST['tname']
    tdesc  = request.POST['tdesc']
    #  create a new query record in the database
    t = Technology(
        name=tname,
        description=tdesc
    )
    t.save()
    return HttpResponseRedirect(reverse('scoping:technologies'))

########################################################
## Add the technology
@login_required
def update_tech(request):

    tid = request.POST['tid']
    tname = request.POST['tname']
    tdesc  = request.POST['tdesc']
    #  create a new query record in the database
    t = Technology.objects.get(pk=tid)
    t.name=tname
    t.description=tdesc
    t.save()
    return HttpResponseRedirect(reverse('scoping:technologies'))



#########################################################
## Do the query
import subprocess
import sys
@login_required
def doquery(request):

    #ssh_test()

    qtitle = request.POST['qtitle']
    qdb    = request.POST['qdb']
    qtype  = request.POST['qtype']
    qtext  = request.POST['qtext']

    #  create a new query record in the database
    q = Query(
        title=qtitle,
        type=qtype,
        text=qtext,
        creator = request.user,
        date = timezone.now(),
        database = qdb
    )
    q.save()

    if qdb=="intern":
        args = qtext.split(" ")
        q1 = Doc.objects.filter(query=args[0])
        op = args[1]
        q2 = Doc.objects.filter(query=args[2])
        if op =="AND":
            combine = q1 | q2
        if op == "NOT":
            combine = q1.exclude(query=args[2])
        for d in combine:
            d.query.add(q)

        q.r_count = len(combine.distinct())
        q.save()

        return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': q.id, 'q2id': 0, 'sbsid': 0}))


    else:
        # write the query into a text file
        fname = "/queries/"+str(q.id)+".txt"
        with open(fname,"w") as qfile:
            qfile.write(qtext)

        time.sleep(1)

    # run "scrapeQuery.py" on the text file in the background
    subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 0, 'docadded': 0, 'q2id': 0}))

#########################################################
## Start snowballing
import subprocess
import sys
@login_required
def start_snowballing(request):

    #ssh_test()

    qtitle = request.POST['sbs_name']
    qtype  = 'backward'
    qtext  = request.POST['sbs_initialpearls']

    qdb = request.POST['qdb']

    curdate = timezone.now()

    sbs = SnowballingSession(
      name = qtitle,
      database = qdb,
      initial_pearls = qtext,
      date=curdate,
      status=0
    )
    sbs.save()

    #  create 2 new query records in the database (one for the bakward search and one for the forward search)
    q = Query(
        title=qtitle+"_backward_1_1",
        database=qdb,
        type=qtype,
        text=qtext,
        date=curdate,
        snowball=sbs.id,
        step=1,
        substep=1
    )
    q.save()

    # write the query into a text file
    fname = "/queries/"+str(q.id)+".txt"
    with open(fname,"w") as qfile:
        qfile.write(qtext)

    # run "scrapeQuery.py" on the text file in the background
    subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

    q2 = Query(
        title=qtitle+"_forward_1_2",
        database=qdb,
        type='forward',
        text=qtext,
        date=curdate,
        snowball=sbs.id,
        step=1,
        substep=2
    )
    q2.save()

    # write the query into a text file
    fname = "/queries/"+str(q2.id)+".txt"
    with open(fname,"w") as qfile:
        qfile.write(qtext)
  
    time.sleep(1)

    # run "scrapeQuery.py" on the text file in the background
    subprocess.Popen(["python3", "/home/hilj/python_apsis_libs/scrapeWoS/bin/snowball_fast.py", "-s", qdb, fname])

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 1, 'docadded': 0, 'q2id': q2.id}))

#########################################################
## Start snowballing
import subprocess
import sys
@login_required
def do_snowballing(request,qid,q2id):

    #ssh_test()
 
    # Backward query
    # Get current query
    query = Query.objects.get(id=qid)
    
    qtitle  = str.split(query.title,"_")[0] 
    qtype   = 'backward'
    qstep   = query.step
    qdb     = "WoS"
    curdate = timezone.now()
    sbsid   = query.snowball 

    # Generate query from selected documents
    #TODO: Tag?
    docs    = DocOwnership.objects.filter(query_id=qid, user_id=request.user, relevant=1)
    docdois = []
    for doc in docs:
        docdoi = WoSArticle.objects.get(doc_id=doc.doc_id)
        docdois.append(docdoi.di)
    doiset  = set(docdois)
    if (len(doiset) > 0):
        # Generate query
        qtext   = 'DO = ("' + '" OR "'.join(doiset) + '")' 

        print(qtext)

        #  create a new query record in the database
        q = Query(
            title=qtitle+"_backward_"+str(qstep+1)+"_1",
            database=qdb,
            type=qtype,
            text=qtext,
            date=curdate,
            snowball=sbsid,
            step=qstep+1,
            substep=1
        )
        q.save()

        # write the query into a text file
        fname = "/queries/"+str(q.id)+".txt"
        with open(fname,"w") as qfile:
            qfile.write(qtext)

        time.sleep(1)

        # run "scrapeQuery.py" on the text file in the background
        subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

        return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 1, 'docadded': 0, 'q2id': 0}))

    else :
        print("No document selected. Select at least one document before snowballing.")
        return HttpResponseRedirect(reverse('scoping:query', kwargs={'qid': q.id}))
      

    # Forward query
    # Get current query
    query_f = Query.objects.get(id=q2id)

    qtitle  = str.split(query_f.title,"_")[0]
    qtype   = 'forward'
    qstep   = query_f.step
    qdb     = "WoS"
    sbsid   = query_f.snowball

    # Generate query from selected documents
    #TODO: Tag?
    docs    = DocOwnership.objects.filter(query_id=q2id, user_id=request.user, relevant=1)
    docdois = []
    for doc in docs:
        docdoi = WoSArticle.objects.get(doc_id=doc.doc_id)
        docdois.append(docdoi.di)
    doiset  = set(docdois)
    if (len(doiset) > 0):
        # Generate query
        qtext   = 'DO = ("' + '" OR "'.join(doiset) + '")'

        print(qtext)

        #  create a new query record in the database
        q = Query(
            title=qtitle+"_forward_"+str(qstep+1)+"_2",
            database=qdb,
            type=qtype,
            text=qtext,
            date=curdate,
            snowball=sbsid,
            step=qstep+1,
            substep=1
        )
        q.save()

        # write the query into a text file
        fname = "/queries/"+str(q.id)+".txt"
        with open(fname,"w") as qfile:
            qfile.write(qtext)

        time.sleep(1)

        # run "scrapeQuery.py" on the text file in the background
        subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

        return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 1, 'docadded': 0, 'q2id': 0}))

    else :
        print("No document to do forward query.")

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 1, 'docadded': 0, 'q2id': 0}))



#########################################################
## Delete the query
@login_required
def delete_query(request, qid):
    try:
        q = Query.objects.get(pk=qid)
        q.delete()
        title = str(qid.id)
        shutil.rmtree("/queries/"+title)
        os.remove("/queries/"+title+".txt")
        os.remove("/queries/"+title+".log")
    except:
        pass
    return HttpResponseRedirect(reverse('scoping:index'))

#########################################################
## Delete the query
@login_required
def delete_tag(request, qid, tid):
    try:
        t = Tag.objects.get(pk=tid)
        t.delete()
    except:
        pass
    return HttpResponseRedirect(reverse('scoping:query', kwargs={'qid': qid}))

#########################################################
## Delete the query
@login_required
def delete_sbs(request, sbsid):
    try:
        sbs = SnowballingSession.objects.get(pk=sbsid)

        # Get associated queries
        qs = Query.objects.filter(snowball=sbsid)

        # Delete SB session
        sbs.delete()

        # Delete asociated queries and files
        #TODO: Could be better handled by cascade function in postgres DB
        for qid in qs :
            q = Query.objects.get(pk=qid)
            q.delete()

            title = str(qid)
            shutil.rmtree("/queries/"+title)
            os.remove("/queries/"+title+".txt")
            os.remove("/queries/"+title+".log")
    except:
        pass
    return HttpResponseRedirect(reverse('scoping:snowball'))

#########################################################
## Add the documents to the database
@login_required
def dodocadd(request):
    qid = request.GET.get('qid',None)
    db  = request.GET.get('db',None)

    q = Query.objects.get(pk=qid)

    if q.dlstat != "NOREC":
        if db=="WoS":
            upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_docs.py'))
        if db=="scopus":
            upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_scopus_docs.py'))

        subprocess.Popen(["python3", upload, qid])
 
        time.sleep(2)

    if q.type == "default":
        substep = 0
    else:
        substep = 2

    #return HttpResponse(upload)
    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': qid, 'substep': substep, 'docadded': 1, 'q2id': 0}))



#########################################################
## Add the documents and their references to the database
@login_required
def dodocrefadd(request):
    qid  = request.GET.get('qid',None)
    qfid = request.GET.get('q2id',None) 

    qf = Query.objects.get(pk=qfid)
    qf.dlstat = "done"
    qf.save()

    db = qf.database

    if db=="WoS":
        upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_docs.py'))
    if db=="scopus":
        print("Not yet implemented")
        exit()

    subprocess.Popen(["python3", upload, qfid]).wait()

    print("upload_docs.py done (citations have been included in the database)")

    #db = request.GET.get('db',None)

    q = Query.objects.get(pk=qid)

    db = q.database

    # Create reference query
    q2 = Query(
        title=str.split(q.title, "_")[0]+"_backward_"+str(q.step)+"_2",
        database=db,
        type="backward",
        text="",
        date=timezone.now(),
        snowball=q.snowball,
        step=q.step,
        substep=2
    )
    q2.save()

    print(q2.title+" has been created! Running upload_docrefs.py...")

    if db=="WoS":
        upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_docrefs.py'))
    if db=="scopus":
        print("Not yet implemented")
        exit()

    subprocess.Popen(["python3", upload, qid, str(q2.id)]).wait()

    print("upload_docrefs.py done")

    fname = "/queries/"+str(q2.id)+".txt"

    print("Check if "+fname+" exists...")
    adddocs = 1
    if os.path.isfile(fname):
        print("Yes... Start scraping")
        subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py", "-s", db, fname])

        time.sleep(2)

        adddocs = 0

    #return HttpResponse(upload)
    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q2.id, 'substep': 2, 'docadded': adddocs, 'q2id': qf.id}))

#########################################################
## Page views progress of query scraping

@login_required
def querying(request, qid, substep, docadded, q2id):

    template = loader.get_template('scoping/query_progress.html')

    query = Query.objects.get(pk=qid)

    if query.type == "default":

    # How many docs are there already added?
        docs      = Doc.objects.filter(query__id=qid)
        doclength = len(docs)

        if doclength == 0: # if we've already added the docs, we don't need to show the log
            logfile = "/queries/"+str(query.id)+".log"

            wait = True
            # wait up to 15 seconds for the log file, then go to a page which displays its contents
            for i in range(15):
                try:
                    with open(logfile,"r") as lfile:
                        log = lfile.readlines()
                    break
                except:
                    log = ["oops, there seems to be some kind of problem, I can't find the log file. Try refreshing a couple of times before you give up and start again."]
                    time.sleep(1)

            finished = False
            if "done!" in log[-1]:
                finished = True
        else:
            log=False
            finished=True

        context = {
            'log': log,
            'finished': finished,
            'docs': docs,
            'doclength': doclength,
            'query': query,
            'substep': substep
        }

    else:

        query2 = Query.objects.get(pk=q2id)

        # How many docs are associated to the query?
        docs      = Doc.objects.filter(query__id=qid)
        doclength = len(docs)

        doclength = 0  # force it for now

        reftotlen   = query.reftotlen
        refdblen    = query.refdblen
        refscraplen = query.refscraplen

        logfile = "/queries/"+str(qid)+".log"
        rstfile = "/queries/"+str(qid)+"/results.txt"
 
        logfile2 = "/queries/"+str(q2id)+".log"
        rstfile2 = "/queries/"+str(q2id)+"/results.txt"

        log = False
        log2 = False

        if not os.path.isfile(rstfile):
            wait = True
            # wait up to 15 seconds for the log file, then go to a page which displays its contents
            for i in range(15):
                try:
                    with open(logfile,"r") as lfile:
                        log = lfile.readlines()
                    break
                except:
                    log = ["oops, there seems to be some kind of problem, I can't find the log file. Try refreshing a couple of times before you give up and start again."]
                    time.sleep(1)
            #        time.sleep(1)
            if query2.dlstat == "done":
                log2 = ["Citations were all captured in the first substep."]
            else :
                for i in range(15):
                    try:
                        with open(logfile2,"r") as lfile:
                            log2 = lfile.readlines()
                        break
                    except:
                        log2 = ["oops, there seems to be some kind of problem, I can't find the log file. Try refreshing a couple of times before you give up and start again."]
                        time.sleep(1)

            finished = False
            if "done!" in log[-1]:
                finished = True
                query.dlstat = ""
                query.save()
            if "WoS couldn't find any records... exiting..." in log[-1]:
                finished = True
                query.dlstat = "NOREC"
                query.save()
        else:
            #og=False
            #og2=False
            finished=True

        context = {
            'log': log,
            'log2': log2,
            'finished': finished,
            'docs': docs,
            'doclength': doclength,
            'reftotlen': reftotlen,
            'refdblen' : refdblen,
            'refscraplen' : refscraplen,
            'query': query,
            'query2': query2,
            'substep':substep,
            'docadded':docadded
        }

    return HttpResponse(template.render(context, request))

############################################################
## SBS - Set default ownership to current user

@login_required
def sbs_allocateDocsToUser(request,qid,q2id):
    
    DEBUG = False 

    #Get queries
    query_b = Query.objects.get(pk=qid)
    query_f = Query.objects.get(pk=q2id)
 
    if DEBUG:
        print("Getting references query: "+str(query_b.title)+" ("+str(qid)+")")
        print("Getting citations query: " +str(query_f.title)+" ("+str(q2id)+")")

    # Get associated docs
    docs_b = Doc.objects.filter(query=qid)
    docs_f = Doc.objects.filter(query=q2id)

    # Define new tag
    tag_b = Tag(
        title = "sbs_"+str(query_b.title)+"_"+str(request.user),
        text  = "",
        query = query_b
    )
    tag_b.save()
    tag_f = Tag(
        title = "sbs_"+str(query_f.title)+"_"+str(request.user),
        text  = "",
        query = query_f
    )
    tag_f.save()

    # Population Docownership table
    for doc in docs_b:
        docown = DocOwnership(
            doc      = doc,
            user     = request.user,
            query    = query_b,
            tag      = tag_b,
            relevant = 1    # Set all documents to keep status by default
        )
        docown.save()

    for doc in docs_f:
        docown = DocOwnership(
            doc      = doc,
            user     = request.user,
            query    = query_f,
            tag      = tag_f,
            relevant = 1    # Set all documents to keep status by default
        )
        docown.save()

    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': query_b.id, 'q2id': query_f.id, 'sbsid': query_b.snowball}))


############################################################
## SBS - Set default ownership to current user

@login_required
def sbs_setAllQDocsToIrrelevant(request,qid,q2id,sbsid):

    DEBUG = True

    #Get query
    query_b = Query.objects.get(pk=qid)
    query_f = Query.objects.get(pk=q2id)

    if DEBUG:
        print("Getting references query: "+str(query_b.title)+" ("+str(qid)+")")
        print("Getting citations query: " +str(query_f.title)+" ("+str(q2id)+")")

    # get latest tag
    tag_b = Tag.objects.filter(query=qid).last()
    tag_f = Tag.objects.filter(query=q2id).last()

    if DEBUG:
        print("Getting references tag: "+str(tag_b.title)+" ("+str(tag_b.text)+")")
        print("Getting citations tag: "+str(tag_f.title)+" ("+str(tag_f.text)+")")

    # Get associated docs
    docs_b = DocOwnership.objects.filter(query=qid, tag=tag_b.id, user=request.user)
    docs_f = DocOwnership.objects.filter(query=q2id, tag=tag_f.id, user=request.user)
    # Population Docownership table
    for doc in docs_b:
        doc.relevant = 2
        doc.save()

    for doc in docs_f:
        doc.relevant = 2
        doc.save()

    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': qid, 'q2id': q2id, 'sbsid': sbsid}))

############################################################
## Query homepage - manage tags and user-doc assignments

@login_required
def query(request,qid):
    template = loader.get_template('scoping/query.html')
    query = Query.objects.get(pk=qid)

    tags = Tag.objects.filter(query=query)

    tags = tags.values()

    for tag in tags:
        tag['docs'] = Doc.objects.filter(tag=tag['id']).distinct().count()
        tag['a_docs'] = Doc.objects.filter(docownership__tag=tag['id']).distinct().count()
        tag['seen_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant__gt=0).count()
        tag['rel_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant=1).count()
        tag['irrel_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant=2).count()
        try:
            tag['relevance'] = round(tag['rel_docs']/(tag['rel_docs']+tag['irrel_docs'])*100)
        except:
            tag['relevance'] = 0

    fields = ['id','title']

    untagged = Doc.objects.filter(query=query).count() - Doc.objects.filter(query=query,tag__query=query).distinct().count()

    users = User.objects.all()

    proj_users = users.query

    user_list = []

    for u in users:
        user_docs = {}
        tdocs = DocOwnership.objects.filter(query=query,user=u)
        user_docs['tdocs'] = tdocs.count()
        if user_docs['tdocs']==0:
            user_docs['tdocs'] = False
        else:
            user_docs['reldocs'] = tdocs.filter(relevant=1).count()
            user_docs['irreldocs'] = tdocs.filter(relevant=2).count()
            user_docs['maybedocs'] = tdocs.filter(relevant=3).count()
            user_docs['yesbuts'] = tdocs.filter(relevant=4).count()
            user_docs['checked_percent'] = round((user_docs['reldocs'] + user_docs['irreldocs'] + user_docs['maybedocs']) / user_docs['tdocs'] * 100)
        if query in u.query_set.all():
            user_list.append({
                'username': u.username,
                'email': u.email,
                'onproject': True,
                'user_docs': user_docs
            })
        else:
            user_list.append({
                'username': u.username,
                'email': u.email,
                'onproject': False,
                'user_docs': user_docs
            })

    context = {
        'query': query,
        'tags': list(tags),
        'fields': fields,
        'untagged': untagged,
        'users': user_list,
        'user': request.user
    }

    #add_manually()



    return HttpResponse(template.render(context, request))

##################################################
## User home page

@login_required
def userpage(request):
    template = loader.get_template('scoping/user.html')

    # Queries
    queries = Query.objects.filter(users=request.user).values('id','type','tag')

    query_list = []

    for qt in queries:
        print(qt['type'])
        q = Query.objects.get(pk=qt['id'])
        tag = Tag.objects.get(pk=qt['tag'])
        ndocs           = Doc.objects.filter(query=q).count()
        dos = DocOwnership.objects.filter(query=q,user=request.user,tag=tag)
        revdocs         = dos.count()
        reviewed_docs   = dos.filter(relevant__gt=0).count()
        unreviewed_docs = revdocs - reviewed_docs
        reldocs   = dos.filter(relevant=1).count()
        irreldocs = dos.filter(relevant=2).count()
        maybedocs = dos.filter(relevant=3).count()
        yesbuts   = dos.filter(relevant=4).count()
        try:
            relevance = round(reldocs/(reldocs+irreldocs)*100)
        except:
            relevance = 0
        query_list.append({
            'id': q.id,
            'tag': tag,
            'type': q.type,
            'title': q.title,
            'ndocs': ndocs,
            'revdocs': revdocs,
            'revieweddocs': reviewed_docs,
            'unreviewed_docs': unreviewed_docs,
            'reldocs': reldocs,
            'maybedocs': maybedocs,
            'yesbuts': yesbuts,
            'relevance': relevance
        })

    query = queries.last()


    # Snowballing sesseions
    sb_sessions     = SnowballingSession.objects.all().order_by('-id')
    
    # Get latest step associated with each SB sessions
    # Initialise variable that will contain the information to be sent to the webpage (context)
    sb_info = []   

    # Loop over SB sessions
    for sbs in sb_sessions:
        sb_info_tmp = {}
        sb_info_tmp['id']     = sbs.id
        sb_info_tmp['name']   = sbs.name
        sb_info_tmp['ip']     = sbs.initial_pearls
        sb_info_tmp['date']   = sbs.date
        sb_info_tmp['status'] = sbs.status

        # Get queries associated with the current SB session
        sb_qs    = Query.objects.filter(snowball = sbs.id).order_by('-id')

        # Initialise step, count and query_info variables
        step     = "1"
        nbdocsel = 0
        nbdoctot = 0
        nbdocrem = 0
        sb_info_tmp['q_info'] = []

        # Loop over queries associated with the current SB session
        cnt = 0 # Query iterator to capture last query (There must be a better way to do that)
        for q in sb_qs:
            # Select reference queries only (sub-step == 2)
            if q.title.split("_")[3] == "2":
                # For old queries
                try: 
                    q_info_tmp             = {} 
                    q_info_tmp['id']       = q.id
                    q_info_tmp['title']    = q.title
                    q_info_tmp['type']     = q.type
                    #q_info_tmp['nbdoctot'] = DocOwnership.objects.filter(query = q, user=request.user).count()
                    #q_info_tmp['nbdocsel'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 1).count()
                    #q_info_tmp['nbdocrev'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 0).count()
                    #q_info_tmp['nbdoctot'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__query = q).count()
                    q_info_tmp['nbdocsel'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count()
                    q_info_tmp['nbdocrem'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()
                    q_info_tmp['nbdoctot'] = q_info_tmp['nbdocsel'] + q_info_tmp['nbdocrem']

                    if cnt == 0:
                        q_info_tmp['last'] = "True"
                    else:
                        q_info_tmp['last'] = "False"

                    sb_info_tmp['q_info'].append(q_info_tmp)
                except:
                    q_info_tmp             = {}
                    q_info_tmp['id']       = q.id
                    q_info_tmp['title']    = q.title
                    q_info_tmp['type']     = q.type
                    #q_info_tmp['nbdoctot'] = DocOwnership.objects.filter(query = q, user=request.user).count()
                    #q_info_tmp['nbdocsel'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 1).count()
                    #q_info_tmp['nbdocrev'] = DocOwnership.objects.filter(query = q, user=request.user, relevant = 0).count()
                    q_info_tmp['nbdoctot'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__query = q).count()
                    q_info_tmp['nbdocsel'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count()
                    q_info_tmp['nbdocrem'] = Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()
 
                    if cnt == 0:
                        q_info_tmp['last'] = "True"
                    else:
                        q_info_tmp['last'] = "False"

                    sb_info_tmp['q_info'].append(q_info_tmp)

                # Get current step
                s = q.title.split("_")[2]
                if s > step:
                    step = s

                # Update total counts
                #nbdoctot += DocOwnership.objects.filter(query = q, user=request.user).count()
                #nbdocsel += DocOwnership.objects.filter(query = q, user=request.user, relevant = 1).count()
                #nbdocrev += DocOwnership.objects.filter(query = q, user=request.user, relevant = 2).count()
                #nbdoctot += Doc.objects.filter(query = q, docownership__user=request.user, docownership__query = q).count()
                nbdocsel += Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count()
                nbdocrem += Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()
                nbdoctot += Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 1, docownership__query = q).count() + Doc.objects.filter(query = q, docownership__user=request.user, docownership__relevant = 2, docownership__query = q).count()

                # Update iterator
                cnt += 1 

        # Update info of current SB session
        sb_info_tmp['ns']    = step
        sb_info_tmp['lq']    = sb_qs.last().id
        sb_info_tmp['rc']    = sb_qs.last().r_count
        sb_info_tmp['ndsel'] = str(nbdocsel)
        sb_info_tmp['ndtot'] = str(nbdoctot)
        sb_info_tmp['ndrem'] = str(nbdocrem)

        # Add SB session info to container
        sb_info.append(sb_info_tmp)


    context = {
        'user': request.user,
        'queries': query_list,
        'query': query,
        'sbsessions': sb_info
    }
    return HttpResponse(template.render(context, request))

##################################################
## Exclude docs from snowballing session
@login_required
def sbsKeepDoc(request,qid,did):

    #Set doc review to 0
    docs = DocOwnership.objects.all(doc=did, query=qid, user=request.user)

    print(docs)


    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': qid, 'q2id': q2id, 'sbsid': sbsid}))

##################################################
## Exclude docs from snowballing session
@login_required
def sbsExcludeDoc(request,qid,did):

    #Set doc review to 0
    docs = DocOwnership.objects.all(doc=did, query=qid, user=request.user)
 
    print(docs)
    

    return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': qid, 'q2id': q2id, 'sbsid': sbsid}))

##################################################
## View all docs
@login_required
def doclist(request,qid,q2id,sbsid):

    template = loader.get_template('scoping/docs.html')
  
    print(str(qid))
    print(str(q2id))

    if qid == 0 or qid=='0':
        qid = Query.objects.all().last().id

    query = Query.objects.get(pk=qid)
    qdocs = Doc.objects.filter(query__id=qid)

    if q2id != '0' and sbsid != '0':
        query_f = Query.objects.get(pk=q2id)
        print(query_f)
        qdocs_f = Doc.objects.filter(query__id=q2id)
        print(qdocs_f)
        all_docs = qdocs | qdocs_f
    else:
        query_f  = False
        all_docs = qdocs

    print(all_docs)

    ndocs = all_docs.count()

    docs = list(all_docs[:500].values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py'))

    print(len(docs))
    #print(docs)


    fields = []

    for f in WoSArticle._meta.get_fields():
        path = "wosarticle__"+f.name
        fields.append({"path": path, "name": f.verbose_name})

    for u in User.objects.all():
        path = "docownership__"+u.username
        fields.append({"path": path, "name": u.username})

    for f in DocAuthInst._meta.get_fields():
        path = "docauthinst__"+f.name
        if f.name !="doc" and f.name !="query":
            fields.append({"path": path, "name": f.verbose_name})

    fields.append({"path": "tag__title", "name": "Tag name"})

    basic_fields = ['Title', 'Abstract', 'Year'] #, str(request.user)]

    context = {
        'query': query,
        'query2' : query_f,
        'docs': docs,
        'fields': fields,
        'basic_fields': basic_fields,
        'ndocs': ndocs,
        'sbsid': sbsid,
    }
    return HttpResponse(template.render(context, request))



from django.db.models.aggregates import Aggregate
class StringAgg(Aggregate):
    function = 'STRING_AGG'
    template = "%(function)s(%(expressions)s, '%(delimiter)s')"

    def __init__(self, expression, delimiter, **extra):
        super(StringAgg, self).__init__(expression, delimiter=delimiter, **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return ''
        return value


##################################################
## View all docs in a Snowball session
@login_required
def doclistsbs(request,sbsid):

    template = loader.get_template('scoping/docs_sbs.html')

    print(str(sbsid))

    if sbsid == 0 or sbsid=='0':
        sbsid = SnowballingSession.objects.all().last().id

    sbs = SnowballingSession.objects.get(pk=sbsid)

    all_docs = []
    queries = Query.objects.filter(snowball=sbsid)

    # Loop over queries
    for q in queries:
        # Filter out non-reference queries
        tmp = str.split(q.title,"_")
        if tmp[len(tmp)-1] == "2":
            qdocs    = Doc.objects.filter(query__id=400,docownership__relevant=1,docownership__query=400) 
#            all_docs.append(qdocs.values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py'))
            qdocs2 = qdocs.values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py')
            for d in qdocs2:
                all_docs.append(d)

    print(type(all_docs))
    print(all_docs)

    ndocs = len(all_docs)

    print(ndocs)

    docs = all_docs
#    docs = list(all_docs[:100].values('UT','wosarticle__ti','wosarticle__ab','wosarticle__py'))

    print(len(docs))
    print(docs)


    fields = []

 #   for f in Doc._meta.get_fields():
 #       if f.is_relation:
 #           for rf in f.related_model._meta.get_fields():
 #               if not rf.is_relation:
 #                   path = f.name+"__"+rf.name
 #                   fields.append({"path": path, "name": rf.verbose_name})
    for f in WoSArticle._meta.get_fields():
        path = "wosarticle__"+f.name
        if f.name !="doc":
            fields.append({"path": path, "name": f.verbose_name})

#    for f in DocOwnership._meta.get_fields():
#        if f.name == "user":
#            path = "docownership__user__username"
#        else:
#            path = "docownership__"+f.name
#        if f.name !="doc" and f.name !="query":
#            fields.append({"path": path, "name": f.verbose_name})

    for u in User.objects.all():
        path = "docownership__"+u.username
        fields.append({"path": path, "name": u.username})

    for f in DocAuthInst._meta.get_fields():
        path = "docauthinst__"+f.name
        if f.name !="doc" and f.name !="query":
            fields.append({"path": path, "name": f.verbose_name})

    fields.append({"path": "tag__title", "name": "Tag name"})

    basic_fields = ['Title', 'Abstract', 'Year'] #, str(request.user)]

    context = {
        'sbs': sbs,
        'docs': docs,
        'fields': fields,
        'basic_fields': basic_fields,
        'ndocs': ndocs,
    }
    return HttpResponse(template.render(context, request))



##################################################
## Ajax function, to return sorted docs



@login_required
def sortdocs(request):

    qid  = request.GET.get('qid',None)
    q2id = request.GET.get('q2id',None)
    fields = request.GET.getlist('fields[]',None)
    field = request.GET.get('field',None)
    sortdir = request.GET.get('sortdir',None)
    extra_field = request.GET.get('extra_field',None)

    f_fields = request.GET.getlist('f_fields[]',None)
    f_operators = request.GET.getlist('f_operators[]',None)
    f_text = request.GET.getlist('f_text[]',None)
    f_join = request.GET.getlist('f_join[]',None)

    sort_dirs = request.GET.getlist('sort_dirs[]',None)
    sort_fields = request.GET.getlist('sort_fields[]',None)

    tag_title = request.GET.get('tag_title',None)
    download = request.GET.get('download',None)   

    # get the query
    query = Query.objects.get(pk=qid)
     
    # filter the docs according to the query 
    if q2id != '0':
        query_f = Query.objects.get(pk=q2id)
        qdocs_f = Doc.objects.filter(query__id=q2id)
        all_docs = Doc.objects.filter(query__id=qid) | qdocs_f
        filt_docs = Doc.objects.filter(query__id=qid) | qdocs_f
    else:
        query_f  = False
        all_docs = Doc.objects.filter(query__id=qid)
        filt_docs = Doc.objects.filter(query__id=qid)
 
    #if "tag__title" in fields:
    #    filt_docs = filt_docs.filter(tag__query__id=qid)

    tag_text = ""
    # filter the docs according to the currently active filter
    for i in range(len(f_fields)):
        if i==0:
            joiner = "AND"
            text_joiner = ""
        else:
            joiner = f_join[i-1]
            text_joiner = f_join[i-1]
        if f_operators[i] == "noticontains":
            op = "icontains"
            exclude = True
        if f_operators[i] == "notexact":
            op = "exact"
            exclude = True
        else:
            op =  f_operators[i]
            exclude = False
        try:
            if "tag__title" in f_fields[i]:
                if q2id != '0':
                    filt_docs = filt_docs.filter(tag__query__id=qid,tag__title__icontains=f_text[i]) | filt_docs.filter(tag__query__id=q2id,tag__title__icontains=f_text[i])
                else:
                    filt_docs = filt_docs.filter(tag__query__id=qid,tag__title__icontains=f_text[i]) 
                tag_filter = f_text[i]
            else: 
                kwargs = {
                    '{0}__{1}'.format(f_fields[i],op): f_text[i]
                }
                if joiner=="AND":
                    if exclude:
                        filt_docs = filt_docs.exclude(**kwargs)
                    else:
                        filt_docs = filt_docs.filter(**kwargs)
                else:
                    if exclude:
                        filt_docs = filt_docs | all_docs.exclude(**kwargs)
                    else:
                        filt_docs = filt_docs | all_docs.filter(**kwargs)
                tag_text+= '{0} {1} {2} {3}'.format(text_joiner, f_fields[i], f_operators[i], f_text[i])
        except:
            break

    print(len(filt_docs))


    if tag_title is not None:
        t = Tag(title=tag_title)
        t.text = tag_text
        t.query = query
        t.save()
        for doc in filt_docs:
            doc.tag.add(t)
        return(JsonResponse("",safe=False))

    if sortdir=="+":
        sortdir=""

    fields = tuple(fields)

    single_fields = ['UT']
    mult_fields = []
    users = []
    for f in fields:
        if "docauthinst" in f or "tag__" in f:
            mult_fields.append(f)
            #single_fields.append(f)
        elif "docownership" in f:
            users.append(f)
        else:
            single_fields.append(f)
    single_fields = tuple(single_fields)
    mult_fields_tuple = tuple(mult_fields)

    #print(mult_fields)

    #mult_fields=[]

    if len(users) > 0:
        uname = users[0].split("__")[1]
        user = User.objects.get(username=uname)
        null_filter = 'docownership__relevant__isnull'
        if q2id!='0':
            reldocs = filt_docs.filter(docownership__user=user,docownership__query=query) | filt_docs.filter(docownership__user=user,docownership__query=query_f)
            if "tag__title" in f_fields:
                reldocs = filt_docs.filter(docownership__user=user,docownership__query=query, docownership__tag__title__icontains=tag_filter) | filt_docs.filter(docownership__user=user,docownership__query=query_f, docownership__tag__title__icontains=tag_filter)
                print(reldocs)
            reldocs = reldocs.values("UT")
            filt_docs = filt_docs.filter(UT__in=reldocs)
        else:
            reldocs = filt_docs.filter(docownership__user=user,docownership__query=query)
            if "tag__title" in f_fields:
                reldocs = filt_docs.filter(docownership__user=user,docownership__query=query, docownership__tag__title__icontains=tag_filter)
                print(reldocs)
            reldocs = reldocs.values("UT")
            filt_docs = filt_docs.filter(UT__in=reldocs)

    #print(len(filt_docs))

    if sort_dirs is not None:
        order_by = ('-PY','UT')
        if len(sort_dirs) > 0:
            order_by = []
        for s in range(len(sort_dirs)):
            sortdir = sort_dirs[s]
            field = sort_fields[s]
            if sortdir=="+":
                sortdir=""
            null_filter = field+'__isnull'
            order_by.append(sortdir+field)
            filt_docs = filt_docs.filter(**{null_filter:False})
        #print(order_by) COMMENTED BECAUSE OF 500 ERROR
        docs = filt_docs.order_by(*order_by).values(*single_fields)[:100]


        if len(mult_fields) > 0:

            for d in docs:
                for m in range(len(mult_fields)):
                    f = (mult_fields_tuple[m],)
                    if "tag__" in mult_fields_tuple[m]:
                        if q2id!='0':
                            adoc = Tag.objects.all().filter(doc__UT=d['UT'],query=qid).values_list("title") | Tag.objects.all().filter(doc__UT=d['UT'],query=q2id).values_list("title")
                        else:
                            adoc = Tag.objects.all().filter(doc__UT=d['UT'],query=qid).values_list("title")
                    else:
                        adoc = filt_docs.filter(UT=d['UT']).values_list(*f).order_by('docauthinst__position')
                    d[mult_fields[m]] = "; <br>".join(str(x) for x in (list(itertools.chain(*adoc))))

    for d in docs:
        if len(users) > 0:
            for u in users:
                uname = u.split("__")[1]
                #print(uname)
                doc = Doc.objects.get(UT=d['UT'])
                #print(d['UT'])
                if q2id!='0':
                    do = DocOwnership.objects.filter(doc_id=d['UT'],query__id=qid,user__username=uname) | DocOwnership.objects.filter(doc_id=d['UT'],query__id=q2id,user__username=uname)
                else:
                    do = DocOwnership.objects.filter(doc_id=d['UT'],query__id=qid,user__username=uname)
                if "tag__title" in f_fields:
                    do = do.filter(tag__title__icontains=tag_filter)
                if do.count() > 0:
                    d[u] = do.first().relevant
                    text = do.first().get_relevant_display()
                    tag = str(do.first().tag.id)
                    user = str(User.objects.filter(username=uname).first().id)
                    if download == "false":
                        d[u] = '<span class="relevant_cycle" data-user='+user+' data-tag='+tag+' data-id='+d['UT']+' data-value='+str(d[u])+' onclick="cyclescore(this)">'+text+'</span>'
        try:
            d['wosarticle__di'] = '<a target="_blank" href="http://dx.doi.org/'+d['wosarticle__di']+'">'+d['wosarticle__di']+'</a>'
        except:
            pass

    if download == "true":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="documents.csv"'

        writer = csv.writer(response)

        writer.writerow(fields)

        for d in docs:
            row = [d[x] for x in fields]
            writer.writerow(row)         

        return response

    #x = zu 
    response = {
        'data': list(docs),
        'n_docs': filt_docs.count()
    }

    template = loader.get_template('scoping/doc.html')
    context = {

    }
    #return HttpResponse(template.render(context, request))

    #x = y
    return JsonResponse(response,safe=False)

def cycle_score(request):

    qid = int(request.GET.get('qid',None))
    q2id = int(request.GET.get('q2id',None))
    score = int(request.GET.get('score',None))
    doc_id = request.GET.get('doc_id',None)
    user = int(request.GET.get('user',None))
    tag = int(request.GET.get('tag',None))

    query = Query.objects.get(id=qid)

    if query.type == "default":
        if score == 4:
            new_score = 0
        else:
            new_score = score+1
        docown = DocOwnership.objects.filter(query__id=qid, doc__UT=doc_id, user__id=user, tag__id=tag).first()
        docown.relevant = new_score
        docown.save()
    else:
        query2 = Query.objects.get(id=q2id)
        if score == 2:
            new_score = 1
        else:
            new_score = score+1

        # Check 
        docown = DocOwnership.objects.filter(query__id=qid, doc__UT=doc_id, user__id=user, tag__id=tag).first()
        if (docown == None):
            docown = DocOwnership.objects.filter(query__id=q2id, doc__UT=doc_id, user__id=user, tag__id=tag).first()

        docown.relevant = new_score
        docown.save()

    return HttpResponse("")

@login_required
@user_passes_test(lambda u: u.is_superuser)
def activate_user(request):

    qid = request.GET.get('qid',None)
    checked = request.GET.get('checked',None)
    user = request.GET.get('user',None)

    query = Query.objects.get(pk=qid)
    user = User.objects.get(username=user)

    if checked=="true":
        query.users.add(user)
        query.save()
        response=1
    else:
        response=-1
        query.users.remove(user)

    return JsonResponse(response,safe=False)

def update_criteria(request):
    qid = request.GET.get('qid',None)
    criteria = request.POST['criteria']

    query = Query.objects.get(pk=qid)
    query.criteria = criteria
    query.save()

    return HttpResponseRedirect(reverse('scoping:query', kwargs={'qid': qid}))

def assign_docs(request):
    qid = request.GET.get('qid',None)
    users = request.GET.getlist('users[]',None)
    tags = request.GET.getlist('tags[]',None)
    tagdocs = request.GET.getlist('tagdocs[]',None)
    docsplit = request.GET.get('docsplit',None)

    #print(docsplit)

    query = Query.objects.get(pk=qid)

    user_list = []

    for user in users:
        user_list.append(User.objects.get(username=user))

    print(tags)

    dos = []

    for tag in range(len(tags)):
        t = Tag.objects.get(pk=tags[tag])
        docs = Doc.objects.filter(query=query,tag=t)
        l= len(docs)
        ssize = int(tagdocs[tag])

        my_ids = list(docs.values_list('UT', flat=True))
        rand_ids = random.sample(my_ids, ssize)
        sample = docs.filter(UT__in=rand_ids).all()
        s = 0
        for doc in sample:
            s+=1
            if docsplit=="true":
                user = user_list[s % len(user_list)]
                docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
                dos.append(docown)
            else:
                for user in user_list:
                    docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
                    dos.append(docown)
    DocOwnership.objects.bulk_create(dos)
    print("Done")

    return HttpResponse("<body>xyzxyz</body>")

import re

## Universal screening function, ctype = type of documents to show
def screen(request,qid,tid,ctype,d=0):
    d = int(d)
    ctype = int(ctype)
    query = Query.objects.get(pk=qid)
    tag = Tag.objects.get(pk=tid)
    user = request.user

    docs = DocOwnership.objects.filter(
            doc__wosarticle__isnull=False,
            query=query,
            user=user.id,
            tag=tag
    )
    if ctype==1:
        docs = docs.filter(relevant__gte=ctype)
    else:
        docs = docs.filter(relevant=ctype)
    if d < 0:
        d = docs.count() - 1

    docs = docs.order_by('date')

    tdocs = docs.count()
    sdocs = d

    ndocs = docs.count()

    try:
        doc_id = docs[d].doc_id
    except:
        return HttpResponseRedirect(reverse('scoping:userpage'))

    pages = ["check","review","review","maybe","yesbut"]

    doc = Doc.objects.filter(UT=doc_id).first()
    authors = DocAuthInst.objects.filter(doc=doc)
    abstract = highlight_words(doc.content,query.text)
    title = highlight_words(doc.wosarticle.ti,query.text)

    qtechs = Technology.objects.filter(query__doc=doc) | Technology.objects.filter(doc=doc)
    qtechs = qtechs.distinct()
    ntechs = Technology.objects.exclude(query__doc=doc).exclude(doc=doc)

    template = loader.get_template('scoping/doc.html')
    context = {
        'query': query,
        'doc': doc,
        'ndocs': ndocs,
        'user': user,
        'authors': authors,
        'tdocs': tdocs,
        'sdocs': sdocs,
        'abstract': abstract,
        'title': title,
        'page': pages[ctype],
        'ctype': ctype,
        'qtechs': qtechs,
        'ntechs': ntechs,
        'tag': tag,
        'd': d
    }

    return HttpResponse(template.render(context, request))

def do_review(request):

    tid = request.GET.get('tid',None)
    qid = request.GET.get('query',None)
    doc_id = request.GET.get('doc',None)
    d = request.GET.get('d',None)

    doc = Doc.objects.get(pk=doc_id)
    query = Query.objects.get(pk=qid)
    user = request.user
    tag = Tag.objects.get(pk=tid)

    docown = DocOwnership.objects.filter(doc=doc,query=query,user=user,tag=tag).order_by("relevant").first()

    print(docown.relevant)

    print(docown.user.username)
    print(docown.doc.UT)

    docown.relevant=int(d)
    docown.date=timezone.now()
    docown.save()
    print(docown.relevant)

    time.sleep(1)
    return HttpResponse("")

def remove_assignments(request):
    qid = request.GET.get('qid',None)
    query = Query.objects.get(pk=qid)
    todelete = DocOwnership.objects.filter(query=query)
    DocOwnership.objects.filter(query=int(qid)).delete()
    return HttpResponse("")


def delete(request,thing,thingid):
    from scoping import models
    getattr(models, thing).objects.get(pk=thingid).delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def add_note(request):
    doc_id = request.POST.get('docn',None)
    tid = request.POST.get('tag',None)
    qid = request.POST.get('qid',None)
    ctype = request.POST.get('ctype',None)
    d = request.POST.get('d',None)
    text = request.POST.get('note',None)

    doc = Doc.objects.get(pk=doc_id)
    note = Note(
        doc=doc,
        user=request.user,
        date=timezone.now(),
        text=text
    )
    note.save()
        

    return HttpResponseRedirect(reverse('scoping:screen', kwargs={
        'qid': qid,
        'tid': tid,
        'ctype': ctype,
        'd': d
    }))




#########################################################
## Download the queryset


def download(request, qid):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="documents.csv"'

    writer = csv.writer(response)

    headers = []

    for f in WoSArticle._meta.get_fields():
        path = "wosarticle__"+f.name
        if f.name !="doc":
            headers.append({"path": path, "name": f.verbose_name})

    for f in DocAuthInst._meta.get_fields():
        path = "docauthinst__"+f.name
        if f.name !="doc" and f.name !="query":
            headers.append({"path": path, "name": f.verbose_name})

    hrow = [x['name'] for x in headers]
    fields = [x['path'] for x in headers]

    writer.writerow(hrow)
    
    q = Query.objects.get(pk=qid)
    docs = Doc.objects.filter(query=q)
    docvals = docs.values(*fields)
    for d in docvals:
        row = [d[x] for x in fields]
        writer.writerow(row)
        

    return response

def doc_tech(request):
    did = request.GET.get('did',None)
    tid = request.GET.get('tid',None)
    doc = Doc.objects.get(pk=did)
    tech = Technology.objects.get(pk=tid)
    doc.technology.add(tech)
    doc.save()
    return HttpResponse()

from django.contrib.auth import logout
def logout_view(request):
    logout(request)
    # Redirect to a success page.
    #return HttpResponse("logout")
    return HttpResponseRedirect(reverse('scoping:index'))

def add_manually():

    qid = 308
    tag = 61
    user = User.objects.get(username="delm")
    query = Query.objects.get(id=qid)
    t = Tag.objects.get(pk=tag)
    docs = Doc.objects.filter(query=query,tag=t).distinct()
    for doc in docs:
        try:
            DocOwnership.objects.get(doc=doc,query=query,user=user,tag=tag)
        except:
            docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
            docown.save()
            print("new docown added")

    return HttpResponse("")

def highlight_words(s,query):
    qwords = re.findall('\w+',query)
    nots = ["TS","AND","NOT","NEAR","OR","and"]
    qwords = set([x for x in qwords if x not in nots])
    abstract = []
    for word in s.split(" "):
        if word in qwords:
            abstract.append('<span class="t1">'+word+'</span>')
        else:
            abstract.append(word)
    return(" ".join(abstract))


