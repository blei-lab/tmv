from django.http import HttpResponse, HttpResponseRedirect
from django.template import Template, Context, RequestContext, loader
from tmv_app.models import *
from django.db.models import Q, F, Sum, Count, FloatField
from django.shortcuts import *
from django.forms import ModelForm
import random, sys, datetime
import urllib.request
from nltk.stem import SnowballStemmer
from django.http import JsonResponse

# the following line will need to be updated to launch the browser on a web server
TEMPLATE_DIR = sys.path[0] + '/templates/'

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]

nav_bar = loader.get_template('tmv_app/nav_bar.html').render()
global run_id

def find_run_id(request):
    try:
        run_id = request['run_id']
    except:
        settings = Settings.objects.all().first()
        run_id = settings.run_id
        try:
            request['run_id'] = run_id
        except:
            pass
    return(int(run_id))

def get_year_filter(request):
    try:
        y1 = request.session['y1']
        y2 = request.session['y2']
    except:
        y1 = 1990
        y2 = 2016
        request.session['y1'] = y1
        request.session['y2'] = y2

    return([y1,y2])

def show_toolbar(request):
    return True
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK" : show_toolbar,
}

def author_detail(request, author_name):
    run_id = find_run_id(request.session)
    response = author_name
    documents = Doc.objects.filter(docauthors__author=author_name)

    topics = {}
    topics = Topic.objects.all()
    topics = []

    for d in documents:
        doctopics = d.doctopic_set.values()
        for dt in doctopics:
            if dt['scaled_score']*100 > 1 :  
                topic = Topic.objects.get(topic=dt['topic_id'])
                if topic in topics:
                    topics[topics.index(topic)].sum += dt['scaled_score']
                else:
                    topic.sum = dt['scaled_score']
                    topics.append(topic)

    topics = DocTopic.objects.filter(doc__docauthors__author=author_name, scaled_score__gt=0.01,run_id=run_id)

    topics = topics.annotate(total=(Sum('scaled_score')))

    topics = topics.values('topic','topic__title').annotate(
        tprop=Sum('scaled_score')
    ).order_by('-tprop')

    pie_array = []
    for t in topics:
        pie_array.append([t['tprop'], '/topic/' + str(t['topic']), 'topic_' + str(t['topic'])])

    author_template = loader.get_template('tmv_app/author.html')

    author_page_context = Context({'nav_bar': nav_bar, 'author': author_name, 'docs': documents, 'topics': topics, 'pie_array': pie_array})

    return HttpResponse(author_template.render(author_page_context))

###########################################################################
## Institution view
def institution_detail(request, institution_name):
    run_id = find_run_id(request.session)
    documents = Doc.objects.filter(docinstitutions__institution__icontains=institution_name).order_by('-PY')

    topics = {}
    topics = Topic.objects.all()
    topics = []

    topics = DocTopic.objects.filter(doc__docinstitutions__institution__icontains=institution_name,  scaled_score__gt=0.00002,run_id=run_id)

    topics = topics.annotate(total=(Sum('scaled_score')))

    topics = topics.values('topic','topic__title').annotate(
        tprop=Sum('scaled_score')
    ).order_by('-tprop')

    pie_array = []
    for t in topics:
        pie_array.append([t['tprop'], '/topic/' + str(t['topic']), 'topic_' + str(t['topic'])])

    institution_template = loader.get_template('tmv_app/institution.html')

    institution_page_context = Context({'nav_bar': nav_bar, 'institution': institution_name, 'docs': documents, 'topics': topics, 'pie_array': pie_array})

    return HttpResponse(institution_template.render(institution_page_context))

def index(request):
    ip = request.META['REMOTE_ADDR']
    return HttpResponse("Hello, " + str(ip) + " You're at the topic browser index.")




###########################################################################
## Topic View
def topic_detail(request, topic_id):    
    #update_year_topic_scores(request.session)
    response = ''
    run_id = find_run_id(request.session)
    stat = RunStats.objects.get(run_id=run_id)
    if stat.get_method_display() == 'hlda':
        return(topic_detail_hlda(request, topic_id))
    
    topic_template = loader.get_template('tmv_app/topic.html')
    
    topic = Topic.objects.get(topic=topic_id,run_id=run_id)
    topicterms = Term.objects.filter(topicterm__topic=topic.topic, run_id=run_id, topicterm__score__gt=0.00001).order_by('-topicterm__score')
    if Settings.objects.first().doc_topic_scaled_score==True:
        doctopics = Doc.objects.filter(doctopic__topic=topic.topic,doctopic__run_id=run_id).order_by('-doctopic__scaled_score')[:50]
    else:
        doctopics = Doc.objects.filter(doctopic__topic=topic.topic,doctopic__run_id=run_id).order_by('-doctopic__score').exclude(UT__contains='2WOS')[:50]
    
    terms = []
    term_bar = []
    remainder = 1
    remainder_titles = ''
    
    for tt in topicterms:
        term = Term.objects.get(term=tt.term)
        score = tt.topicterm_set.all()[0].score
        
        terms.append(term)
        if score >= .00001:
            term_bar.append((True, term, score * 100))
            remainder -= score
        else:
            if remainder_titles == '':
                remainder_titles += term.title
            else:
                remainder_titles += ', ' + term.title
    term_bar.append((False, remainder_titles, remainder*100))

    #update_year_topic_scores()

    yts = TopicYear.objects.filter(run_id=run_id)  

    ytarray = list(yts.values('PY','count','score','topic_id','topic__title'))
    #ytarray = []
    
    corrtops = TopicCorr.objects.filter(topic=topic_id).order_by('-score')[:10]

    ctarray = []

    for ct in corrtops:
        top = Topic.objects.get(topic=ct.topiccorr)
        if ct.score < 1:
            score = round(ct.score,2)
            ctarray.append({"topic": top.topic,"title":top.title,"score":score})
  
    topic_page_context = Context({'nav_bar': nav_bar, 'topic': topic, 'terms': terms, 'term_bar': term_bar, 'docs': doctopics, 'yts': ytarray, 'corrtops': ctarray})
    
    return HttpResponse(topic_template.render(topic_page_context))

###########################################################################
## Topic View for HLDA
def topic_detail_hlda(request, topic_id):    
    #update_year_topic_scores(request.session)
    response = ''
    run_id = find_run_id(request.session)
    
    topic_template = loader.get_template('tmv_app/topic.html')
    
    topic = HTopic.objects.get(topic=topic_id,run_id=run_id)
    topicterms = Term.objects.filter(htopicterm__topic=topic.topic, run_id=run_id).order_by('-htopicterm__count')[:10]
    doctopics = Doc.objects.filter(hdoctopic__topic=topic.topic,hdoctopic__run_id=run_id)
    
    terms = []
    term_bar = []
    remainder = 1
    remainder_titles = ''
    
    for tt in topicterms:
        term = Term.objects.get(term=tt.term)
        
        terms.append(term)

#            term_bar.append((True, term, score * 100))
#            remainder -= score
#        else:
#            if remainder_titles == '':
#                remainder_titles += term.title
#            else:
#                remainder_titles += ', ' + term.title
#    term_bar.append((False, remainder_titles, remainder*100))

    update_year_topic_scores(request.session)

    yts = HTopicYear.objects.filter(run_id=run_id)  

    ytarray = list(yts.values('PY','count','score','topic_id','topic__title'))
    #ytarray = []
    
    corrtops = TopicCorr.objects.filter(topic=topic_id).order_by('-score')[:10]

    ctarray = []

    for ct in corrtops:
        top = Topic.objects.get(topic=ct.topiccorr)
        if ct.score < 1:
            score = round(ct.score,2)
            ctarray.append({"topic": top.topic,"title":top.title,"score":score})
  
    topic_page_context = Context({'nav_bar': nav_bar, 'topic': topic, 'terms': terms, 'term_bar': term_bar, 'docs': doctopics, 'yts': ytarray, 'corrtops': ctarray})
    
    return HttpResponse(topic_template.render(topic_page_context))

##############################################################

def term_detail(request, term_id):
    update_topic_titles(request.session)
    run_id = find_run_id(request.session)
    response = ''

    term_template = loader.get_template('tmv_app/term.html')
    
    term = Term.objects.get(term=term_id,run_id=run_id)
    
    topics = {}
    for topic in Topic.objects.filter(run_id=run_id):
        tt = TopicTerm.objects.filter(topic=topic.topic, term=term_id,run_id=run_id)
        if len(tt) > 0:
            topics[topic] = tt[0].score
    
    sorted_topics = sorted(topics.keys(), key=lambda x: -topics[x])
    topic_tuples = []

    
    if len(topics.keys()) > 0:
        max_score = max(topics.values())
        for topic in sorted_topics:
            topic_tuples.append((topic, topics[topic], topics[topic]/max_score*100))

    topics = TopicTerm.objects.filter(term=term_id,run_id=run_id).order_by('-score')
    if len(topics) > 0:
        topic_tuples = []
        max_score = topics[0].score
        for topic in topics:
            topic_tuples.append((topic.topic, topic.score, topic.score/max_score*100))
    

    term_page_context = Context({'nav_bar': nav_bar, 'term': term, 'topic_tuples': topic_tuples})
    
    return HttpResponse(term_template.render(term_page_context))

#######################################################################
## Doc view

def doc_detail(request, doc_id):

    snowball_stemmer = SnowballStemmer("english")

    run_id = find_run_id(request.session)
    stat = RunStats.objects.get(run_id=run_id)
    if stat.get_method_display() == 'hlda':
        return(doc_detail_hlda(request, doc_id))
    update_topic_titles(request.session)
    response = ''
    doc_template = loader.get_template('tmv_app/doc.html')
    
    doc = Doc.objects.get(UT=doc_id)

    doctopics = DocTopic.objects.filter(doc=doc_id,run_id=run_id).order_by('-score')

    doc_authors = DocAuthors.objects.filter(doc__UT=doc_id).distinct('author')

    doc_institutions = DocInstitutions.objects.filter(doc__UT=doc_id)
    for di in doc_institutions:
        di.institution = di.institution.split(',')[0]
    
    topics = []
    pie_array = []
    dt_threshold = Settings.objects.get(id=1).doc_topic_score_threshold
    dt_thresh_scaled = Settings.objects.get(id=1).doc_topic_scaled_score
    topicwords = {}
    ntopic = 0
    for dt in doctopics:
#        if ((not dt_thresh_scaled and dt.score >= dt_threshold) or (dt_thresh_scaled and dt.scaled_score*100 >= dt_threshold)):
        if ((dt_thresh_scaled and dt.scaled_score*80 >= dt_threshold) or
            (not dt_thresh_scaled and dt.score >= dt_threshold)):
            topic = Topic.objects.get(topic=dt.topic_id)
            ntopic+=1
            topic.ntopic = "t"+str(ntopic)
            topics.append(topic)
            terms = Term.objects.filter(topicterm__topic=topic.topic).order_by('-topicterm__score')[:10]
            
            topicwords[ntopic] = []
            for tt in terms:
                topicwords[ntopic].append(tt.title)
            if not dt_thresh_scaled:
                pie_array.append([dt.score, '/topic/' + str(topic.topic), 'topic_' + str(topic.topic)])
            else:
                pie_array.append([dt.scaled_score, '/topic/' + str(topic.topic), 'topic_' + str(topic.topic)])

   
    words = []
    for word in doc.content.split():
        wt = ""
        for t in range(1,ntopic+1):
            #if snowball_stemmer.stem(word) in topicwords[t]:
            if word in topicwords[t]:
                wt = t
        words.append({'title': word, 'topic':"t"+str(wt)})
    
    doc_page_context = Context({'nav_bar': nav_bar, 'doc': doc, 'topics': topics, 'pie_array': pie_array,'doc_authors': doc_authors, 'doc_institutions': doc_institutions , 'words': words })
    
    return HttpResponse(doc_template.render(doc_page_context))


############################################################################
## for HLDA
def doc_detail_hlda(request, doc_id):

    snowball_stemmer = SnowballStemmer("english")

    run_id = find_run_id(request.session)

    update_topic_titles(request.session)
    response = ''
    doc_template = loader.get_template('tmv_app/doc.html')
    
    doc = Doc.objects.get(UT=doc_id)

    doctopics = HDocTopic.objects.filter(doc=doc_id,run_id=run_id).order_by('level')

    doc_authors = DocAuthors.objects.filter(doc__UT=doc_id).distinct('author')

    doc_institutions = DocInstitutions.objects.filter(doc__UT=doc_id)
    for di in doc_institutions:
        di.institution = di.institution.split(',')[0]
    
    topics = []
    pie_array = []
    
    topicwords = {}
    ntopic = 0
    for dt in doctopics:
        topic = HTopic.objects.get(topic=dt.topic_id)
        ntopic+=1
        topic.ntopic = "t"+str(ntopic)
        topics.append(topic)
        terms = Term.objects.filter(htopicterm__topic=topic.topic).order_by('-htopicterm__count')[:10]
        
        topicwords[ntopic] = []
        for tt in terms:
            topicwords[ntopic].append(tt.title)
        pie_array.append([dt.score, '/topic/' + str(topic.topic), 'topic_' + str(topic.topic)])

   
    words = []
    for word in doc.content.split():
        wt = ""
        for t in range(1,ntopic+1):
            if snowball_stemmer.stem(word) in topicwords[t]:
                wt = t
        words.append({'title': word, 'topic':"t"+str(wt)})
    
    doc_page_context = Context({'nav_bar': nav_bar, 'doc': doc, 'topics': topics, 'pie_array': pie_array,'doc_authors': doc_authors, 'doc_institutions': doc_institutions , 'words': words })
    
    return HttpResponse(doc_template.render(doc_page_context))


def topic_list_detail(request):
    run_id = find_run_id(request.session)
    update_topic_titles()
    response = ''
    
    template_file = open(TEMPLATE_DIR + 'topic_list.html', 'r')
    list_template = Template(template_file.read())
    
    topics = Topic.objects.all()

    terms = []
    for t in topics:
        topicterms = TopicTerm.objects.filter(topic=t.topic).order_by('-score')[:5]
        temp =[]
        term_count = 5
        for tt in topicterms:
            temp.append(Term.objects.get(term=tt.term))
            term_count -= 1
        for i in range(term_count):        
            temp.append(None)
        terms.append(temp)

    div_topics = []
    div_terms = []
    rows = []
    n = 3
    for i in xrange(0, len(topics), n):
        temp = [] 
        for j in range(5):
            K = min(len(topics), i+n)
            t = [terms[k][j] for k in range(i,K,1)]
            while len(t) < n:
                t.append(None)
            temp.append(t)
        tops = topics[i:i+n]
        while len(tops) < n:
            tops.append(None)
        rows.append((tops, temp))

    list_page_context = Context({'nav_bar': nav_bar, 'rows': rows})
    
    return HttpResponse(list_template.render(list_page_context))

#################################################################
### Main page!
def topic_presence_detail(request):
    run_id = find_run_id(request.session)
    stat = RunStats.objects.get(run_id=run_id)
    if stat.get_method_display() == 'hlda':
        return(topic_presence_hlda(request))
        
    update_topic_titles(request.session)
    update_topic_scores(request.session)
    response = ''

    get_year_filter(request)
    
    presence_template = loader.get_template('tmv_app/topic_presence.html')

    topics = Topic.objects.filter(run_id=run_id).order_by('-score')
    max_score = topics[0].score

    topic_tuples = []
    for topic in topics:
        topic_tuples.append((topic, topic.score, topic.score/max_score*100))

    presence_page_context = Context({'nav_bar': nav_bar, 'topic_tuples': topic_tuples})
    
    return HttpResponse(presence_template.render(presence_page_context))

##################################################################
## Alt Main page for hlda

def topic_presence_hlda(request):
    run_id = find_run_id(request.session)
    update_topic_titles_hlda(request.session)
    update_topic_scores(request.session)
    response = ''

    get_year_filter(request)
    
    presence_template = loader.get_template('tmv_app/topic_presence_hlda.html')

    topics = HTopic.objects.filter(run_id=run_id).order_by('-n_docs')
    max_score = topics[0].n_docs

    topic_tuples = []

    ttree = "{"

    for topic in topics:
        topic_tuples.append((topic, topic.n_docs, topic.n_docs/max_score*100))

    topics = topics.values()

    root = topics[0]
    root['children'] = []
    root['parent_id'] = "null"

    for topic in topics:
        if topic['parent_id']==root['topic']:
            topic['children'] = []
            for child in topics:
                if child['parent_id']==topic['topic']:
                    child['children'] = []
                    for grandchild in topics:
                        if grandchild['parent_id']==child['topic']:
                            child['children'].append(grandchild)
                    topic['children'].append(child)
            root['children'].append(topic)

    presence_page_context = Context({'nav_bar': nav_bar, 'topic_tuples': topic_tuples,'topic_tree': root})
    
    return HttpResponse(presence_template.render(presence_page_context))

def get_docs(request):
    topic = request.GET.get('topic',None)
    t = HTopic.objects.get(topic=topic)
    topic_box_template = loader.get_template('tmv_app/topic_box.html')
    docs = Doc.objects.filter(hdoctopic__topic=topic).order_by('hdoctopic__score')[:5].values()
    data = {
        "bla": "bla"
    }
    topic_box_context = Context({'docs':docs, 'topic':t})
    return HttpResponse(topic_box_template.render(topic_box_context))

def stats(request):
    run_id = find_run_id(request.session)

    stats_template = loader.get_template('tmv_app/stats.html')

    stats = RunStats.objects.get(run_id=run_id)

    if stats.get_method_display() == 'hlda':
        docs_seen = HDocTopic.objects.filter(run_id=run_id).values('doc_id').order_by().distinct().count()
    else:
        docs_seen = DocTopic.objects.filter(run_id=run_id).values('doc_id').order_by().distinct().count()

    stats.docs_seen = docs_seen

    stats.save()

    stats_page_context = Context({'nav_bar': nav_bar, 'num_docs': Doc.objects.count(),'topics_seen': docs_seen, 'num_topics': Topic.objects.filter(run_id=run_id).count(), 'num_terms': Term.objects.filter(run_id=run_id).count(), 'start_time': stats.start, 'elapsed_time': stats.start, 'num_batches': stats.batch_count, 'last_update': stats.last_update})


    return HttpResponse(stats_template.render(stats_page_context))

def runs(request):

    run_id = find_run_id(request.session)
    runs_template = loader.get_template('tmv_app/runs.html')

    stats = RunStats.objects.all().order_by('-start')

    for stat in stats:
        stat_run_id = stat.run_id
        if stat.get_method_display() == 'hlda':
            stat.topics = HTopic.objects.filter(run_id=stat_run_id).count()  
        else:
            stat.topics = Topic.objects.filter(run_id=stat_run_id).count()        
        stat.terms = Term.objects.filter(run_id=stat_run_id).count()


    runs_page_context = Context({'nav_bar': nav_bar, 'stats':stats, 'run_id':run_id})

    #return HttpResponse(runs_template.render(runs_page_context))

    return(render(request, 'tmv_app/runs.html', {'nav_bar': nav_bar, 'stats':stats, 'run_id':run_id}))

class SettingsForm(ModelForm):
    class Meta:
        model = Settings
        fields = '__all__'

def settings(request):
    run_id = find_run_id(request)

    settings_template = loader.get_template('tmv_app/settings.html')
   
    settings_page_context = Context({'nav_bar': nav_bar, 'settings': Settings.objects.get(id=1)})

    return HttpResponse(settings_template.render(settings_page_context))
    #return render_to_response('settings.html', settings_page_context, context_instance=RequestContext(request))

def apply_settings(request):
    settings = Settings.objects.get(id=1)
    form = SettingsForm(request.POST, instance=settings)
    #TODO: add in checks for threshold (make sure it's a float)
    settings.doc_topic_score_threshold = float(request.POST['threshold'])
  
    settings.save()

    return HttpResponseRedirect('/topic_list')

from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render

def update_run(request, run_id):
    try:
        stat = RunStats.objects.get(run_id=run_id)
        stat.notes = request.POST['notes']
        stat.save()
    except:
        pass
    
    return HttpResponseRedirect(reverse('tmv_app:runs'))

def apply_run_filter(request,new_run_id):
#    settings = Settings.objects.get(id=1)
#    settings.run_id = new_run_id
#    settings.save()
    request.session['run_id'] = new_run_id

    return HttpResponseRedirect('/tmv_app/runs')

def delete_run(request,new_run_id):
    stat = RunStats.objects.get(run_id=new_run_id)
    stat.delete()
    terms = Term.objects.filter(run_id=new_run_id)
    terms.delete()
    topics = Topic.objects.filter(run_id=new_run_id)
    topics.delete()
    dt = DocTopic.objects.filter(run_id=new_run_id)
    dt.delete()
    tt = TopicTerm.objects.filter(run_id=new_run_id)
    tt.delete()
    ht = HTopic.objects.filter(run_id=new_run_id)
    ht.delete()
    hd = HDocTopic.objects.filter(run_id=new_run_id)
    

    return HttpResponseRedirect('/tmv_app/runs')

def update_topic_titles(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)
    stats = RunStats.objects.get(run_id=run_id)
    if not stats.topic_titles_current:
    #if "a" in "ab":
        for topic in Topic.objects.filter(run_id=run_id):
            #topicterms = TopicTerm.objects.filter(topic=topic.topic).order_by('-score')[:3]
            topicterms = Term.objects.filter(topicterm__topic=topic.topic).order_by('-topicterm__score')[:3]
            new_topic_title = '{'
            for tt in topicterms:
                new_topic_title +=tt.title
                new_topic_title +=', '
            new_topic_title = new_topic_title[:-2]
            new_topic_title+='}'

            topic.title = new_topic_title
            topic.save()
        stats.topic_titles_current = True
        stats.save()

def update_topic_titles_hlda(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)

    stats = RunStats.objects.get(run_id=run_id)
    if not stats.topic_titles_current:
    #if "a" in "ab":
        for topic in HTopic.objects.filter(run_id=run_id):
            #topicterms = TopicTerm.objects.filter(topic=topic.topic).order_by('-score')[:3]
            topicterms = Term.objects.filter(htopicterm__topic=topic.topic).order_by('-htopicterm__count')[:3]
            new_topic_title = '{'
            for tt in topicterms:
                new_topic_title +=tt.title
                new_topic_title +=', '
            new_topic_title = new_topic_title[:-2]
            new_topic_title+='}'

            topic.title = new_topic_title
            topic.save()
        stats.topic_titles_current = True
        stats.save()


def update_topic_scores(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)
    stats = RunStats.objects.get(run_id=run_id)
    #if "a" in "ab":
    if not stats.topic_scores_current:

        topics = Topic.objects.filter(run_id=run_id)
        for t in topics:
            t.score=0
            t.save()

        topics = DocTopic.objects.filter(run_id=run_id).values('topic').annotate(
            total=Sum('score')
        )
        for tscore in topics:
            topic = Topic.objects.get(topic=tscore['topic'])
            topic.score = tscore['total']
            topic.save()

        stats.topic_scores_current = True
        stats.save()

def update_year_topic_scores(session):
    if isinstance(session, int):
        run_id=session
    else:
        run_id = find_run_id(session)
    stats = RunStats.objects.get(run_id=run_id)
    #if "a" in "a":    
    if not stats.topic_year_scores_current:
        if stats.get_method_display() == 'hlda':
            yts = HDocTopic.objects.filter(doc__PY__gt=1989,run_id=run_id)  

            yts = yts.values('doc__PY').annotate(
                yeartotal=Count('doc')
            )

            ytts = yts.values().values('topic','topic__title','doc__PY').annotate(
                score=Count('doc')
            )
            HTopicYear.objects.filter(run_id=run_id).delete()
            for ytt in ytts:
                yttyear = ytt['doc__PY']
                topic = HTopic.objects.get(topic=ytt['topic'])
                for yt in yts:
                    ytyear = yt['doc__PY']
                    if yttyear==ytyear:
                        yeartotal = yt['yeartotal']
                try:
                    topicyear = HTopicYear.objects.get(topic=topic,PY=yttyear, run_id=run_id)
                except:
                    topicyear = HTopicYear(topic=topic,PY=yttyear,run_id=run_id)
                topicyear.score = ytt['score']
                topicyear.count = yeartotal
                topicyear.save()
        else:
            yts = DocTopic.objects.filter(doc__PY__gt=1989,run_id=run_id)  

            yts = yts.values('doc__PY').annotate(
                yeartotal=Sum('scaled_score')
            )

            ytts = yts.values().values('topic','topic__title','doc__PY').annotate(
                score=Sum('scaled_score')
            )
            TopicYear.objects.filter(run_id=run_id).delete()
            for ytt in ytts:
                yttyear = ytt['doc__PY']
                topic = Topic.objects.get(topic=ytt['topic'])
                for yt in yts:
                    ytyear = yt['doc__PY']
                    if yttyear==ytyear:
                        yeartotal = yt['yeartotal']
                try:
                    topicyear = TopicYear.objects.get(topic=topic,PY=yttyear, run_id=run_id)
                except:
                    topicyear = TopicYear(topic=topic,PY=yttyear,run_id=run_id)
                topicyear.score = ytt['score']
                topicyear.count = yeartotal
                topicyear.save()



        stats.topic_year_scores_current = True
        stats.save()
        

def topic_random(request):
    return HttpResponseRedirect('/tmv_app/topic/' + str(random.randint(1, Topic.objects.count())))

def doc_random(request):
    return HttpResponseRedirect('/tmv_app/doc/' + str(random.randint(1, Doc.objects.count())))

def term_random(request):
    return HttpResponseRedirect('/tmv_app/term/' + str(random.randint(1, Term.objects.count())))

