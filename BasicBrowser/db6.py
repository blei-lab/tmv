import django
from django.utils import timezone
import urllib.parse
import os

import math
import threading, datetime
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")

django.setup()

from tmv_app.models import *

def init(method='lda'):

    global run_id
    try:
        stats = RunStats.objects.all().last()
        settings = Settings.objects.all().first()
        run_id = stats.run_id
    except:
        settings = Settings(
            doc_topic_score_threshold=1, 
            doc_topic_scaled_score=True
        )    
        run_id = 0

    run_id +=1
        
    stats = RunStats(
        run_id = run_id, 
        method=method,
        start=timezone.now(), 
        batch_count=0, 
        last_update=timezone.now()
    )
    stats.save()
    
    settings.run_id = run_id
    settings.save()

    return(run_id)

def increment_batch_count():
    django.db.connections.close_all()
    stats = RunStats.objects.get(run_id=run_id)
    stats.batch_count += 1
    stats.last_update = timezone.now()
    stats.topic_titles_current = False
    stats.topic_scores_current = False
    stats.topic_year_scores_current = False
    print ( stats.last_update )
    stats.save()


def add_terms(vocab):
    global term_diff
    for x in vocab:
        title = x[1]
        gid = x[0]
        term = Term(title=title,run_id=run_id)  
        term.save()
    term_diff = term.term - gid
   

def add_topics(no_topics):
    global t_diff
    for t in range(0,no_topics):
        title = "Topic " + str(t+1)
        topicrow = Topic(title=title,run_id=run_id)
        topicrow.save()
    t_diff = topicrow.topic - t


def add_doc(title,content,docID,UT,PY,AU):
    try:
        doc = Doc.objects.get(UT=doc_id)
    except:
        doc = Doc(title=urllib.parse.unquote(title), content=urllib.parse.unquote(content),UT=UT,PY=PY)
        doc.save()
        AUlist = str(AU)
        for au in AUlist.split("\n"):
            docauth = DocAuthors(doc=doc,author=au.strip())
            docauth.save()

def update_doc(d):
    doc = Doc.objects.get(UT=d.UT)
    article = Article(
        doc = doc,
        TI = d.TI,
        AB = d.AB,
        PY = d.PY,
        TC = d.TC # times cited
    )
    article.save()
    try:
        doc = Doc.objects.get(UT=d.UT)
        article = Article(
            doc = doc,
            TI = d.TI,
            AB = d.AB,
            PY = d.PY,
            TC = d.TC # times cited
            #AR = d.AR,
#            BN = d.BN, # ISBN
#            #BP = d.BP, # beginning page
#            C1 = d.C1, # author address
#            CL = d.CL, # conf location
#            CT = d.CT, # conf title
#            DE = d.DE, # keywords - separate table?
#            DI = d.DI, # DOI
#            DT = d.DT,
#            EM = d.EM,
#            EP = d.EP,
#            FU = d.FU, #funding agency + grant number
#            FX = d.FX, # funding text
#            GA = d.GA, # document delivery number
#            HO = d.HO, # conference host
#            ID = d.ID, # keywords plus ??
#            #IS = d.IS,
#            J9 = d.J9, # 29 char source abbreviation
#            JI = d.JI, # ISO source abbrev
#            LA = d.LA, # Language
#            NR = d.NR, # number of references
#            PA = d.PA, # pub address
#            PD = d.PD, # pub month
#            #PG = d.PG, # page count
#            PI = d.PI, # pub city
#            PT = d.PT, # pub type
#            PU = d.PU, # publisher
#            RP = d.RP, # reprint address
#            SC = d.SC, # subj category
#            SE = d.SE, # book series title
#            SI = d.SI, # special issue
#            SN = d.SN, # ISSN
#            SO = d.SO, # publication name
#            SP = d.SP, # conf sponsors
#            SU = d.SU, # supplement        
            #VL = d.VL, # volume
        )
        article.save()
#        AUlist = str(AU)
#        for au in AUlist.split("\n"):
#            docauth = DocAuthors(doc=doc,author=au.strip())
#            docauth.save()
    except:
        print("not saved")

def update_docinstitute(d):
    doc = Doc.objects.get(UT=d.UT)
    try:
        institutes = d.C1.split("\n")
        for inst in d.C1.split("\n"):
            inst = inst.split("] ")[1]
            try:
                DocInstitutions.objects.get(doc=doc,institution=inst.strip())
            except:
                docinst = DocInstitutions(doc=doc,institution=inst.strip())
                docinst.save()
    except:
        pass

def update_topiccorr(topic_id,corrtopic,score,run_id):
    topic = Topic.objects.get(topic=topic_id)
    try:
        topiccorr = TopicCorr.objects.get(topic=topic, topiccorr=corrtopic, run_id=run_id)
    except:
        topiccorr = TopicCorr(topic=topic,topiccorr=corrtopic,run_id=run_id)
    topiccorr.score = score
    topiccorr.save()

def update_doccorr(doc_id,corrdoc,score,run_id):
    doc = Doc.objects.get(UT=topic_id)
    try:
        doccorr = DocCorr.objects.get(doc=doc, doccorr=corrdoc, run_id=run_id)
    except:
        doccorr = DocCorr(doc=doc, doccorr=corrdoc ,run_id=run_id)
    doccorr.score = score
    doccorr.save()

def docdiff(d):
    django.db.connections.close_all()
    last_doc = Doc.objects.all().last()
    doc_diff = last_doc.doc - d
    return(doc_diff)


def add_doc_topic(doc_id, topic_id, score, scaled_score, run_id):
    django.db.connections.close_all()
    if score < 1:
        return
    doc = Doc.objects.get(UT=doc_id)
    topic = Topic.objects.get(topic=topic_id)
    dt = DocTopic(doc=doc, topic=topic, score=score, scaled_score=scaled_score, run_id=run_id)
    dt.save()
    django.db.connections.close_all()


def clear_topic_terms(topic):
    try:
        TopicTerm.objects.filter(topic=(topic),run_id=run_id).delete()
    except:
        return

def add_topic_term(topic_id, term_no, score, run_id):
    if score >= .00001:
        topic = Topic.objects.get(topic=topic_id)
        term = Term.objects.get(term=term_no)
        tt = TopicTerm(topic=(topic), term=(term), score=score,run_id=run_id)
        tt.save()



