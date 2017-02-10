from django.db import models

#################################################
## Below are some special model variants for hlda
## method

class HTopic(models.Model):
    topic = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', null=True)
    title = models.CharField(max_length=80, null=True)
    n_docs = models.IntegerField(null=True)
    n_words = models.IntegerField(null=True)
    scale = models.FloatField(null=True)    
    run_id = models.IntegerField(null=True, db_index=True)

class HTopicTerm(models.Model):
    topic = models.ForeignKey('HTopic')
    term = models.ForeignKey('Term')
    count = models.IntegerField()
    run_id = models.IntegerField(null=True, db_index=True)

class HDocTopic(models.Model):
    doc = models.ForeignKey('Doc')
    topic = models.ForeignKey('HTopic')
    level = models.SmallIntegerField()
    score = models.FloatField(null=True)
    run_id = models.IntegerField(null=True, db_index=True)
    



#################################################
## Topic, Term and Doc are the three primary models
class Topic(models.Model):
    topic = models.AutoField(primary_key=True)
    title = models.CharField(max_length=80)
    score = models.FloatField(null=True)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)

class TopicCorr(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    topiccorr = models.IntegerField()
    score = models.FloatField(null=True)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)

class Term(models.Model):    
    term = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    run_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return str(self.title)

class Doc(models.Model):
    title = models.TextField(null=True)
    content = models.TextField(null=True)
    UT = models.CharField(max_length=30,db_index=True,primary_key=True)
    PY = models.IntegerField(null=True)
    modkey = models.IntegerField(null=True,db_index=True)
    
    def word_count(self):
        return len(str(self.content).split())

##############################################
## Article holds more WoS type information for each doc

class Article(models.Model):
    doc = models.OneToOneField(
        Doc,
        on_delete=models.CASCADE,
        primary_key=True
    )
    ti = models.TextField(null=True)
    ab = models.TextField(null=True)   
    py = models.IntegerField(null=True) 
    ar = models.IntegerField(null=True) # Article number
    bn = models.CharField(max_length=100) # ISBN
    bp = models.IntegerField(null=True) # beginning page
    c1 = models.TextField(null=True) # author address
    cl = models.TextField(null=True) # conf location
    ct = models.TextField(null=True) # conf title
    de = models.TextField(null=True) # keywords - separate table?
    di = models.CharField(null=True, max_length=150) # DOI
    dt = models.CharField(null=True, max_length=50) # doctype
    em = models.EmailField(null=True) #email 
    ep = models.IntegerField(null=True) # last page
    fn = models.CharField(null=True, max_length=100) # filename?
    fu = models.TextField(null=True) #funding agency + grant number
    fx = models.TextField(null=True) # funding text
    ga = models.CharField(null=True, max_length=100) # document delivery number
    ho = models.TextField(null=True) # conference host
    #ID = models.TextField() # keywords plus ??
    j9 = models.CharField(null=True, max_length=30) # 29 char source abbreviation
    ji = models.CharField(null=True, max_length=50) # ISO source abbrev
    la = models.CharField(null=True, max_length=50) # Language
    nr = models.IntegerField(null=True) # number of references
    pa = models.TextField(null=True) # pub address
    pd = models.CharField(null=True, max_length=5) # pub month
    pg = models.IntegerField(null=True) # page count
    pi = models.TextField(null=True) # pub city
    pt = models.CharField(null=True, max_length=50) # pub type
    pu = models.TextField(null=True) # publisher
    rp = models.TextField(null=True) # reprint address
    sc = models.TextField(null=True) # subj category
    se = models.TextField(null=True) # book series title
    si = models.TextField(null=True) # special issue
    sn = models.CharField(null=True, max_length=50) # ISSN
    so = models.CharField(null=True, max_length=50) # publication name
    sp = models.TextField(null=True) # conf sponsors
    su = models.TextField(null=True) # supplement
    tc = models.IntegerField(null=True) # times cited
    vl = models.IntegerField(null=True)

    
    def word_count(self):
        return len(str(self.content).split())

#################################################
## DocAuthor holds the authors in a doc
class DocAuthors(models.Model):
    doc = models.ForeignKey('Doc',null=True)
    author = models.CharField(max_length=60)

#################################################
## Institutions
class DocInstitutions(models.Model):
    doc = models.ForeignKey('Doc',null=True)
    institution = models.TextField(null=True)

#################################################
## TopicYear holds per year topic totals
class TopicYear(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    PY = models.IntegerField()
    score = models.FloatField()
    count = models.FloatField()
    run_id = models.IntegerField(db_index=True)

#################################################
## Separate topicyear for htopic 
class HTopicYear(models.Model):
    topic = models.ForeignKey('HTopic',null=True)
    PY = models.IntegerField()
    score = models.FloatField()
    count = models.FloatField()
    run_id = models.IntegerField(db_index=True)

#################################################
## DocTopic and TopicTerm map contain topic scores
## for docs and topics respectively

class DocTopic(models.Model):
    doc = models.ForeignKey('Doc', null=True, db_index=True)
    topic = models.ForeignKey('Topic',null=True,db_index=True)
    score = models.FloatField()
    scaled_score = models.FloatField()
    run_id = models.IntegerField(db_index=True)

class TopicTerm(models.Model):
    topic = models.ForeignKey('Topic',null=True)
    term = models.ForeignKey('Term',null=True)
    score = models.FloatField()
    run_id = models.IntegerField(db_index=True)


#################################################
## Not sure what this does???????? not actually used,
## but should it be?
class DocTerm(models.Model):
    doc = models.IntegerField()
    term = models.IntegerField()
    score = models.FloatField()

#################################################
## RunStats and Settings....
class RunStats(models.Model):
    run_id = models.IntegerField(primary_key=True)
    start = models.DateTimeField()
    batch_count = models.IntegerField()
    last_update = models.DateTimeField()
    topic_titles_current = models.NullBooleanField()
    topic_scores_current = models.NullBooleanField()
    topic_year_scores_current = models.NullBooleanField()
    docs_seen = models.IntegerField(null=True)
    notes = models.TextField(null=True)
    LDA = 'LD'
    HLDA = 'HL'
    DTM = 'DT'
    METHOD_CHOICES = (
        (LDA, 'lda'),
        (HLDA, 'hlda'),
        (DTM, 'dtm'),
    )
    method = models.CharField(
        max_length=2,
        choices=METHOD_CHOICES,
        default=LDA,
    )

class Settings(models.Model):
    run_id = models.IntegerField()
    doc_topic_score_threshold = models.FloatField()
    doc_topic_scaled_score = models.BooleanField()
