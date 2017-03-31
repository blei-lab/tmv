import os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from mongoengine import *
from urllib.parse import urlparse, parse_qsl
connect('mongoengine_documents')


class scopus_doc(DynamicDocument):
    scopus_id = StringField(required=True, max_length=50, unique=True)
    PY = IntField(required=True)

class scopus_ref(Document):
    text = StringField(required=True, unique=True)
    ti = StringField()
    PY = IntField()
    extra = StringField()
    doi = StringField()
    url = URLField()
    

scopus_ref.objects.all().delete()

def parse_ref(r):
    ref = {}
    ref['text'] = r
    regurl = '(?:.*)(https?://[^\s,]+)'
    if re.match(regurl,r):
        ref['url'] = re.search(regurl,r).group(1)
    ypat = '(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)'
    if re.match(ypat,r):
        s = re.search('(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)',str(r))
        ref['ti'] = re.split('([A-Z]\.), ',s.group(1))[-1].strip()
        ref['PY'] = s.group(2)
        ref['extra'] = s.group(3)
    if re.match('(.*)DOI:? (.*)',r):
        DOI = re.search('DOI:? (.*)',r)
        ref['doi'] = DOI.group(1)
   
    return ref

i = 0
r_count = 0
for doc in scopus_doc.objects.filter(References__exists=True):
    i+=1
    if i > 100*10000000000:
        break
    for r in doc.References:
        r_count +=1
        ref = parse_ref(r)
        try:
            s = scopus_ref(**ref)
            s.save()
        except:
            pass

print(r_count)

print(scopus_ref.objects.count())

