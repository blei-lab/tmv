#!/usr/bin/env python3

import gensim
import django
import db3 as db

def iter_docs(texts, stoplist, stemmer):
    for text in texts:
        yield (stemmer.stem(x) for x in
                gensim.utils.tokenize(text, lowercase=True, deacc=True, 
                                  errors="ignore")
                if x not in stoplist and len(x) > 2)

class MyCorpus(object):
    def __init__(self, texts, stoplist, stemmer):
        self.texts = texts
        self.stoplist = stoplist
        self.dictionary = gensim.corpora.Dictionary(iter_docs(texts, stoplist, stemmer))

    def __iter__(self):
        for tokens in iter_docs(self.texts, self.stoplist):
            yield self.dictionary.doc2bow(tokens)

class MiniCorpus(object):
    def __init__(self, texts, stoplist, dictionary, stemmer):
        self.texts = texts
        self.stoplist = stoplist
        self.dictionary = dictionary
        self.stemmer = stemmer

    def __iter__(self):
        for tokens in iter_docs(self.texts, self.stoplist, self.stemmer):
            yield self.dictionary.doc2bow(tokens)

def f_doc(d):
    django.db.connections.close_all()
    db.add_doc(d[0],d[1],d[2],d[3],d[4],d[5])
    django.db.connections.close_all()

def f_gamma(d,docset,gamma,docUTset):
    django.db.connections.close_all()
    doc_size = len(docset[d])
    doc_id = docUTset[d]
    for k in range(len(gamma[d])):
        db.add_doc_topic(doc_id, k, gamma[d][k], gamma[d][k]/doc_size)
    django.db.connections.close_all()	

def f_lambda(topic_no,ldalambda):
    django.db.connections.close_all()
    lambda_sum = sum(ldalambda[topic_no])
    db.clear_topic_terms(topic_no)
    for term_no in range(len(ldalambda[topic_no])):
        db.add_topic_term(topic_no, term_no, ldalambda[topic_no][term_no]/lambda_sum)
    django.db.connections.close_all()
