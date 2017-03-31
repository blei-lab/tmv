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

def f_lambda(ldalambda, topic_no):
    django.db.connections.close_all()
    lambda_sum = sum(ldalambda[topic_no])
    db.clear_topic_terms(topic_no)
    topic = Topic.objects.get(topic=topic_no)
    for term_no in range(len(ldalambda[topic_no])):
        term = Term.objects.get(term=term_no)
        db.add_topic_term(topic, term, ldalambda[topic_no][term_no]/lambda_sum)
    django.db.connections.close_all()


class DBManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = "DB Manager"
        self.tasks = []
        self.current = None
        self.end = False
        self.task_count = 0
    def add(self, task):
        self.tasks.append(task)
        #print ( "* %s %s: added" % (datetime.datetime.now(), task.name) )
    def add_start(self, task):
        self.tasks.insert(0, task)
        print ( "* %s %s: added (to start of queue)" % (datetime.datetime.now(), task.name) )
    def cancel_task(self, task):
        self.tasks.remove(task)
        print ( "* %s %s: canceled" % (datetime.datetime.now(), task.name) )
    def get_ident(self):
        self.task_count += 1
        return self.task_count
    def run(self):
        while not self.end or len(self.tasks) != 0:
            if len(self.tasks) != 0:
                self.current = self.tasks.pop(0)
                if self.current and not self.current.cancel:
                    try:
                        self.current.run()
                    except:
                        self.tasks.insert(0, self.current)

DB_LOCK = threading.Lock()
DBM = DBManager()
#DBM.start()

def init():
    stats = RunStats(start=timezone.now(), batch_count=0, last_update=timezone.now())
    stats.save()
    
    settings = Settings(doc_topic_score_threshold=1, doc_topic_scaled_score=True)
    settings.save()

def signal_end():
    DBM.end = True

def increment_batch_count():
    #DB_LOCK.acquire()
    django.db.connections.close_all()
    stats = RunStats.objects.get(id=1)
    stats.batch_count += 1
    stats.last_update = timezone.now()
    stats.topic_titles_current = False
    stats.topic_scores_current = False
    stats.topic_year_scores_current = True
    print ( stats.last_update )
    stats.save()
    #DB_LOCK.release()

def print_task_update():
    print ("** CURRENT TASKS **")
    tasks = DBM.tasks[:]
    if DBM.current:
        tasks.insert(0, DBM.current)
    for task in tasks:
        active = "active" if task == DBM.current else "waiting"
        canceled = task.cancel
        print ( "   %s %s\t\t%s\t\t%s" % (task.time_created, task.name, canceled, active) )
    print ( "** END **" )

class DBTask():
    def __init__(self, name):
        self.cancel = False
        self.time_created = datetime.datetime.now()
        self.ident = DBM.get_ident()
        self.name = "DB Task-%s (%s)" % (self.ident, name)
    def safe_cancel(self):
        self.cancel = True        
        print ( "* %s %s: canceled" % (datetime.datetime.now(), self.name) )
    def run(self):
        #print ( "* %s %s: started" % (datetime.datetime.now(), self.name) )
        #DB_LOCK.acquire()
        #print ( "* %s %s: DB lock acquired" % (datetime.datetime.now(), self.name) )
        self.db_write()
        #DB_LOCK.release()
        #print ( "* %s %s: DB lock released" % (datetime.datetime.now(), self.name) )
        #print ( "* %s %s: ended" % (datetime.datetime.now(), self.name) )
    def db_write(self):
        pass

class TermsTask(DBTask):
    def __init__(self, terms):
        self.terms = terms[1]
        self.ids = terms[0]
        DBTask.__init__(self, "write all terms")
    def db_write(self):
        for i in range(0, len(self.terms)):
            title = self.terms[i]
            gid = self.ids[i]
            add_term(title,gid)

def add_terms(terms):
    DBM.add(TermsTask(terms))

def add_term(title,gid):
    term = Term(term=gid,title=title)
    
    term.save()

def add_topic(t):
    title = "Topic " + str(t+1)
    topicrow = Topic(title=title,topic=t)
    topicrow.save()

def add_topics(no_topics):
    for t in range(0,no_topics):
        add_topic(t)


def add_doc(title,content,docID,UT,PY,AU):
    doc = Doc(title=urllib.parse.unquote(title), content=urllib.parse.unquote(content),doc=docID,UT=UT,PY=PY)
    doc.save()
    AUlist = str(AU)
    for au in AUlist.split("\n"):
        docauth = DocAuthors(doc=doc,author=au.strip())
        docauth.save()

def add_auth(UT,AU):    
    docauth = DocAuthors(UT=UT,author=AU)
    docauth.save()


def add_doc_topic(doc_id, topic_id, score, scaled_score):
    if score < 1:
        return
    doc = Doc.objects.get(doc=doc_id)
    topic = Topic.objects.get(topic=topic_id)
    dt = DocTopic(doc=doc, topic=topic, score=score, scaled_score=scaled_score)
    dt.save()

# deleted plus 1 because now we're working with from 0 gensim_ids
def clear_topic_terms(topic):
    try:
        TopicTerm.objects.filter(topic=(topic)).delete()
    except:
        return

def add_topic_term(topic_no, term_no, score):
    if score >= .005:
        topic = Topic.objects.get(topic=topic_no)
        term = Term.objects.get(term=term_no)
        tt = TopicTerm(topic=(topic), term=(term), score=score)
        tt.save()

class UpdateTopicTermsTask(DBTask):
    def __init__(self, no_topics, topic_terms):
        self.no_topics = no_topics
        self.topic_terms = topic_terms
        DBTask.__init__(self, "update topic terms")
    def db_write(self):
        for topic in range(self.no_topics):
            clear_topic_terms(topic)
        for tt in self.topic_terms:
            add_topic_term(tt[0], tt[1], tt[2])

def update_topic_terms(no_topics, topic_terms):
    for task in DBM.tasks:
        if isinstance(task, UpdateTopicTermsTask):
            task.safe_cancel()
            DBM.cancel_task(task)

    DBM.add_start(UpdateTopicTermsTask(no_topics, topic_terms))
