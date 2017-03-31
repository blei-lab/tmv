#!/usr/bin/env python3

import pickle, string, numpy, getopt, sys, random, time, re, pprint, gc
import pandas as pd
import onlineldavb
import scrapeWoS
import gensim
import nltk
import sys
import time
from multiprocess import Pool
import django
import os
import numpy as np
from functools import partial
sys.stdout.flush()

# import file for easy access to browser database
sys.path.append('/home/galm/software/tmv_dtm/BasicBrowser/')

# sys.path.append('/home/max/Desktop/django/BasicBrowser/')
import db5 as db



def readInfo(p):
    d = {}
    with open(p) as f:
        for line in f:
            (key, val) = line.strip().split(' ',1)
            try:
                d[key] = int(val)
            except:            
                d[key] = val
    return(d)

def f_doc(d):
    django.db.connections.close_all()
    db.add_doc(d[0],d[1],d[2],d[3],d[4],d[5])
    django.db.connections.close_all()

def f_gamma(d):
    django.db.connections.close_all()
    doc_size = len(docset[d])
    doc_id = docUTset[d]
    for k in range(len(gamma[d])):
        db.add_doc_topic(doc_id, k, gamma[d][k], gamma[d][k]/doc_size)
    django.db.connections.close_all()

def f_lambda(topic_no):
    django.db.connections.close_all()
    lambda_sum = sum(ldalambda[topic_no])
    db.clear_topic_terms(topic_no)
    for term_no in range(len(ldalambda[topic_no])):
        db.add_topic_term(topic_no, term_no, ldalambda[topic_no][term_no]/lambda_sum)
    django.db.connections.close_all()

def dtm_doc(d,info,gamma):
    django.db.connections.close_all()
    d_sum = sum(gamma[d])
    for k in range(len(gamma[d])):
        score = gamma[d][k]
        if score > 0.0001:
            db.add_doc_topic_dtm(d, k+info['first_topic'], score, score/d_sum)

def lda_topic(topic_n,info,beta):
    print(topic_n)
    django.db.connections.close_all()

    tbeta = beta[topic_n]
    for t in range(len(tbeta)): # for each term in topic
        score = np.exp(tbeta[t])
        if score > 0.001:
            db.add_topic_term(topic_n+info['first_topic'], t+info['first_word'], score)
    django.db.connections.close_all()

def main():

    db.init()

    path = sys.argv[1]

    os.chdir(path)

    info = readInfo("ldac_out/final.other")

    print(info)


    ## Add docs to db
    d = 0
    with open("lda/dtm-mult.dmap") as f:
            for doc in f:
                UT = doc.split("-")[-1].split(".")[0]
                db.add_doc_simple(UT,d)
                d+=1    

    ## Add terms to db
    with open("lda/dtm-mult.vocab", "r") as f:
        for word in f:
            db.add_term(word.strip())

    ## Add topics
    db.add_topics(info['num_topics'])

    info['first_word'] = db.first_word()
    info['first_topic'] = db.first_topic()

    #############################################
    ## Add doctopic scores from gamma

    gamma = np.fromfile('ldac_out/final.gamma', dtype=float,sep=" ")
    gamma = gamma.reshape((len(gamma)/info['num_topics'],info['num_topics']))

    docs = range(len(gamma))

    pool = Pool(processes=8)
    pool.map(partial(dtm_doc,info=info,gamma=gamma),docs)
    pool.terminate()
    gc.collect()

    beta = np.fromfile('ldac_out/final.beta', dtype=float, sep=" ")
    beta = beta.reshape(info['num_topics'],info['num_terms'])

    topics = range(info['num_topics'])
    pool = Pool(processes=8)
    pool.map(partial(lda_topic,info=info,beta=beta),topics)
    pool.terminate()
    gc.collect()

################################################
    ## Open up the WoS file
    df = scrapeWoS.readWoS('results.txt')
    # filter articles with missing abstracts, and only include articles and reviews
    df = df[(pd.notnull(df.AB)) & (pd.notnull(df.UT)) & (df.DT.isin(["Article","Review"]))].reset_index()

    django.db.connections.close_all()
    for index, row in df.iterrows():
        db.update_doc_simple(row)

if __name__ == '__main__':
	t0 = time.time()	
	main()
	totalTime = time.time() - t0

	tm = int(totalTime//60)
	ts = int(totalTime-(tm*60))

	print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
