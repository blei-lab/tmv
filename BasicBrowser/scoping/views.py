from django.shortcuts import render
import os, time, math, itertools

# Create your views here.

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import loader
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test


from .models import *


def super_check(user):
    return user.groups.filter(name__in=['superuser'])

########################################################
## Homepage - list the queries, form for adding new ones

@login_required
def index(request):

    template = loader.get_template('scoping/index.html')

    queries_none  = Query.objects.all().filter(type=None)
    queries_dft   = Query.objects.all().filter(type="default")
    queries       = queries_none | queries_dft
    queries       = queries.order_by('-id')
    query         = queries.last()
    users         = User.objects.all()
    technologies  = Technology.objects.all()

    context = {
      'queries'      : queries,
      'query'        : query,
      'users'        : users,
      'active_users' : users.filter(username=request.user.username),
      'techs'        : technologies
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
        t.docs = len(t.doc_set.all())

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
    context = {
        'sb_sessions': sb_sessions,
        'sb_session_last': sb_session_last
    }
    return HttpResponse(template.render(context, request))

#########################################################
## Test the SSH connection
def ssh_test():
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

    ssh_test()

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

        return HttpResponseRedirect(reverse('scoping:doclist', kwargs={'qid': q.id}))


    else:
        # write the query into a text file
        fname = "/queries/"+str(q.id)+".txt"
        with open(fname,"w") as qfile:
            qfile.write(qtext)

        time.sleep(1)

    # run "scrapeQuery.py" on the text file in the background
    subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 0}))

#########################################################
## Start snowballing
import subprocess
import sys
@login_required
def start_snowballing(request):

    ssh_test()

    qtitle = request.POST['sbs_name']
    qtype  = 'backward'
    qtext  = request.POST['sbs_initialpearls']

    qdb = "WoS"

    curdate = timezone.now()

    sbs = SnowballingSession(
      name = qtitle,
      initial_pearls = qtext,
      date=curdate
    )
    sbs.save()

    #  create a new query record in the database
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

    time.sleep(1)

    # run "scrapeQuery.py" on the text file in the background
    subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py","-s", qdb, fname])

    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q.id, 'substep': 1, 'docadded': 0}))


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
    db = request.GET.get('db',None)

    if db=="WoS":
        upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_docs.py'))
    if db=="scopus":
        upload = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','upload_scopus_docs.py'))

    subprocess.Popen(["python3", upload, qid])

    time.sleep(2)


    #return HttpResponse(upload)
    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': qid, 'substep': 0, 'docadded': 1}))



#########################################################
## Add the documents and their references to the database
@login_required
def dodocrefadd(request):
    qid = request.GET.get('qid',None)
    db = request.GET.get('db',None)

    q = Query.objects.get(pk=qid)

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

    subprocess.Popen(["python3", upload, qid, str(q2.id)])

    time.sleep(5)

    print("upload_docrefs.py done")

    fname = "/queries/"+str(q2.id)+".txt"


    print("Check if "+fname+" exists...")
    if os.path.isfile(fname):
        print("Yes... Start scraping")
        # run "scrapeQuery.py" on the text file in the background
        subprocess.Popen(["python3", "/home/galm/software/scrapewos/bin/scrapeQuery.py", "-s", db, fname])

        time.sleep(2)

    #return HttpResponse(upload)
    return HttpResponseRedirect(reverse('scoping:querying', kwargs={'qid': q2.id, 'substep': 2, 'docadded': 1}))

#########################################################
## Page views progress of query scraping

@login_required
def querying(request, qid, substep, docadded):

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
        # How many docs are associated to the query?
        docs      = Doc.objects.filter(query__id=qid)
        doclength = len(docs)

        doclength = 0  # force it for now

        logfile = "/queries/"+str(qid)+".log"
        rstfile = "/queries/"+str(qid)+"/results.txt"
 
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
            'substep':substep,
            'docadded':docadded
        }

    return HttpResponse(template.render(context, request))

############################################################
## Query homepage - manage tags and user-doc assignments

@login_required
def query(request,qid):
    template = loader.get_template('scoping/query.html')
    query = Query.objects.get(pk=qid)

    tags = Tag.objects.filter(query=query)

    tags = tags.values()

    for tag in tags:
        tag['docs'] = Doc.objects.filter(tag=tag['id']).count()
        tag['a_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],).count()
        if tag['a_docs'] == 0:
            tag['a_docs'] = False
        else:
            tag['a_docs'] = Doc.objects.filter(docownership__tag=tag['id'],docownership__isnull=False).distinct().count()
            tag['seen_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant__gt=0).count()
            tag['rel_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant=1).count()
            tag['irrel_docs'] = DocOwnership.objects.filter(doc__tag=tag['id'],relevant=2).count()
            try:
                tag['relevance'] = round(tag['rel_docs']/(tag['rel_docs']+tag['irrel_docs'])*100)
            except:
                tag['relevance'] = 0

    fields = ['id','title','text']

    untagged = Doc.objects.filter(query=query,tag__isnull=True).count()

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
    queries = Query.objects.filter(users=request.user)

    query_list = []

    for q in queries:
        ndocs = Doc.objects.filter(query=q).count()
        revdocs = DocOwnership.objects.filter(query=q,user=request.user).count()
        reviewed_docs = DocOwnership.objects.filter(query=q,user=request.user,relevant__gt=0).count()
        unreviewed_docs = revdocs - reviewed_docs
        reldocs = DocOwnership.objects.filter(query=q,user=request.user,relevant=1).count()
        irreldocs = DocOwnership.objects.filter(query=q,user=request.user,relevant=2).count()
        maybedocs = DocOwnership.objects.filter(query=q,user=request.user,relevant=3).count()
        yesbuts = DocOwnership.objects.filter(query=q,user=request.user,relevant=4).count()
        try:
            relevance = round(reldocs/(reldocs+irreldocs)*100)
        except:
            relevance = 0
        query_list.append({
            'id': q.id,
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

    context = {
            'user': request.user,
            'queries': query_list,
        'query': query
    }
    return HttpResponse(template.render(context, request))

##################################################
## Exclude docs from snowballing session
@login_required
def sbsExcludeDoc(request,qid):

    #Set doc review to 0

    return HttpResponseRedirect(reverse('scoping:review_docs', kwargs={'qid': qid,'d': tdocs}))

##################################################
## View all docs
@login_required
def doclist(request,qid):

    template = loader.get_template('scoping/docs.html')

    if qid == 0 or qid=='0':
        qid = Query.objects.all().last().id

    query = Query.objects.get(pk=qid)
    qdocs = Doc.objects.filter(query__id=qid)
    all_docs = qdocs
    ndocs = all_docs.count()

    docs = list(all_docs[:100].values('wosarticle__ti','wosarticle__ab','wosarticle__py'))

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

    basic_fields = ['Title', 'Abstract', 'Year']

    context = {
        'query': query,
        'docs': docs,
        'fields': fields,
        'basic_fields': basic_fields,
        'ndocs': ndocs
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
## Ajax function, to return sorted docs



@login_required
def sortdocs(request):

    qid = request.GET.get('qid',None)
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

    # get the query
    query = Query.objects.get(pk=qid)

    # filter the docs according to the query
    all_docs = Doc.objects.filter(query__id=qid)
    filt_docs = Doc.objects.filter(query__id=qid)

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
        else:
            op =  f_operators[i]
            exclude = False
        try:
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
        if "docauthinst" in f:
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
        reldocs = filt_docs.filter(docownership__user=user,docownership__query=query).values("UT")
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

            #fdocs = filt_docs.order_by(*order_by)[:100]
            #adocs = fdocs.annotate(
            #    **{mult_fields[0]:StringAgg(mult_fields[0],"; ")}
            #).values(*mult_fields)

            for d in docs:
                for m in range(len(mult_fields)):
                    f = (mult_fields_tuple[m],)
                    adoc = Doc.objects.filter(UT=d['UT']).values_list(*f).order_by('docauthinst__position')
                    d[mult_fields[m]] = "; <br>".join(str(x) for x in (list(itertools.chain(*adoc))))

    for d in docs:
        if len(users) > 0:
            for u in users:
                uname = u.split("__")[1]
                #print(uname)
                doc = Doc.objects.get(UT=d['UT'])
                #print(d['UT'])
                do = DocOwnership.objects.filter(doc_id=d['UT'],user__username=uname)
                if do.count() > 0:
                    d[u] = do.first().relevant
                    tag = str(do.first().tag.id)
                    user = str(User.objects.filter(username=uname).first().id)
                    d[u] = '<span class="relevant_cycle" data-user='+user+' data-tag='+tag+' data-id='+d['UT']+' onclick="cyclescore(this)">'+str(d[u])+'</span>'
        try:
            d['wosarticle__di'] = '<a target="_blank" href="http://dx.doi.org/'+d['wosarticle__di']+'">'+d['wosarticle__di']+'</a>'
        except:
            pass




    response = {
        'data': list(docs),
        'n_docs': filt_docs.count()
    }

    template = loader.get_template('scoping/doc.html')
    context = {

    }
    #return HttpResponse(template.render(context, request))

    return JsonResponse(response,safe=False)

def cycle_score(request):

    qid = int(request.GET.get('qid',None))
    score = int(request.GET.get('score',None))
    doc_id = request.GET.get('doc_id',None)
    user = int(request.GET.get('user',None))
    tag = int(request.GET.get('tag',None))


    if score == 4:
        new_score = 0
    else:
        new_score = score+1
    docown = DocOwnership.objects.filter(query__id=qid, doc__UT=doc_id, user__id=user, tag__id=tag).first()
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


    for tag in range(len(tags)):
        t = Tag.objects.get(pk=tags[tag])
        docs = Doc.objects.filter(query=query,tag=t)
        ssize = int(tagdocs[tag])
        sample = docs.order_by('?')[:ssize]
        for s in range(ssize):
            doc = sample[s]
            if docsplit=="true":
                user = user_list[s % len(user_list)]
                docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
                docown.save()
            else:
                for user in user_list:
                    docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
                    docown.save()

    return HttpResponse("bla")

import re

def check_docs(request,qid):

    query = Query.objects.get(pk=qid)
    user = request.user
    docs = DocOwnership.objects.filter(query=query,user=user.id,relevant=0)


    tdocs = Doc.objects.filter(query=query,users=user.id).count()
    sdocs = Doc.objects.filter(query=query,users=user.id, docownership__relevant__gt=0).count()

    ndocs = docs.count()

    try:
        doc_id = docs.first().doc_id
    except:
        return HttpResponseRedirect(reverse('scoping:userpage'))

    doc = Doc.objects.filter(UT=doc_id).first()
    authors = DocAuthInst.objects.filter(doc=doc)
    abstract = highlight_words(doc.content,query.text)
    title = highlight_words(doc.wosarticle.ti,query.text)

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
        'title': title
    }
    return HttpResponse(template.render(context, request))

def back_review(request,qid):
    query = Query.objects.get(pk=qid)
    user = request.user
    docs = DocOwnership.objects.filter(query=query,user=user.id,relevant__gt=0)
    tdocs = docs.count() - 1
    return HttpResponseRedirect(reverse('scoping:review_docs', kwargs={'qid': qid,'d': tdocs}))

def review_docs(request,qid,d=0):
    d = int(d)
    query = Query.objects.get(pk=qid)
    user = request.user

    docs = DocOwnership.objects.filter(query=query,user=user.id,relevant__gt=0)

    tdocs = docs.count()
    sdocs = d

    ndocs = docs.count()
    try:
        doc_id = docs[d].doc_id
    except:
        return HttpResponseRedirect(reverse('scoping:userpage'))

    doc = Doc.objects.filter(UT=doc_id).first()
    authors = DocAuthInst.objects.filter(doc=doc)
    abstract = highlight_words(doc.content,query.text)
    title = highlight_words(doc.wosarticle.ti,query.text)

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
        'title': title
    }
    return HttpResponse(template.render(context, request))

def maybe_docs(request,qid,d=0):
    d = int(d)
    query = Query.objects.get(pk=qid)
    user = request.user

    docs = DocOwnership.objects.filter(query=query,user=user.id,relevant=3)

    tdocs = docs.count()
    sdocs = d

    ndocs = docs.count()
    doc_id = docs[d].doc_id
    doc = Doc.objects.filter(UT=doc_id).first()
    authors = DocAuthInst.objects.filter(doc=doc)
    abstract = highlight_words(doc.content,query.text)
    title = highlight_words(doc.wosarticle.ti,query.text)

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
        'title': title
    }
    return HttpResponse(template.render(context, request))

def do_review(request):

    qid = request.GET.get('query',None)
    doc_id = request.GET.get('doc',None)
    d = request.GET.get('d',None)

    doc = Doc.objects.get(pk=doc_id)
    query = Query.objects.get(pk=qid)
    user = request.user

    docown = DocOwnership.objects.filter(doc=doc,query=query,user=user).order_by("relevant").first()

    docown.relevant=d
    docown.save()

    time.sleep(1)

    return HttpResponse("")

def remove_assignments(request):
    qid = request.GET.get('qid',None)
    query = Query.objects.get(pk=qid)
    todelete = DocOwnership.objects.filter(query=query)
    DocOwnership.objects.filter(query=int(qid)).delete()
    return HttpResponse("")


from django.contrib.auth import logout
def logout_view(request):
    logout(request)
    # Redirect to a success page.
    #return HttpResponse("logout")
    return HttpResponseRedirect(reverse('scoping:index'))

def add_manually():


    qid = 48
    tag = 18
    user = User.objects.get(username="fuss")
    DocOwnership.objects.filter(user=user).delete()
    query = Query.objects.get(id=qid)
    t = Tag.objects.get(pk=tag)
    docs = Doc.objects.filter(docownership__query=query,docownership__tag=t).distinct()
    for doc in docs:
        docown = DocOwnership(doc=doc,query=query,user=user,tag=t)
        docown.save()

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
