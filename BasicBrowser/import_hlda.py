#!/usr/bin/env python3

import argparse, time
import numpy as np
import django
from django.utils import timezone
import datetime, os
import sys
import db6 as db

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")

django.setup()

from tmv_app.models import *


def read_state(filename, terms):

    topics = []
    twords = []

    with open(args.file, 'r') as state:
        score         = float(state.readline().split()[1])
        iter          = int(state.readline().split()[1])
        eta           = state.readline().split()
        eta           = [float(x) for x in eta[1:len(eta)]]
        gam           = state.readline().split()
        gam           = [float(x) for x in gam[1:len(gam)]]
        gem_mean      = float(state.readline().split()[1])
        gem_scale     = float(state.readline().split()[1])
        scaling_shape = float(state.readline().split()[1])
        scaling_scale = float(state.readline().split()[1])

        header = state.readline()
        tree = {}
        for line in state:

            (id, parent, ndocs, nwords, scale, word_cnt) = line.split(None, 5)

            topics.append({'id': id, 
                'parent': parent, 
                'ndocs': ndocs, 
                'nwords': nwords,
                'scale': scale
            })


            words = [int(x) for x in word_cnt.split()]
            twords.append(words)

    return([topics,twords])

def read_dmap(dmap):
    docs = []
    with open(dmap,'r') as dmap:
        for line in dmap:
            d = 'WOS:'+line.strip().split('WOS:')[1].split('.')[0]
            docs.append(d)
    return(docs)

def read_vocab(vocab):
    words = []
    with open(vocab,'r') as vocab:
        for line in vocab:
            w = line.strip()
            words.append({'term': w})
    return(words)

def main(filename, dmap, vocab):
    # Init run
    run_id = db.init('HL')

    # Add docs
    docs = read_dmap(dmap)

    # Add terms
    terms = read_vocab(vocab)
    for term in terms:
        t = Term(title=term['term'],run_id=run_id)
        t.save()
        term['db_id'] = t.term
               
    

    # Add topics
    state = read_state(filename, terms)
    topics = state[0]

    for topic in topics:
        scale = topic['scale']
        nwords = topic['nwords']
        ndocs = topic['ndocs']
        t = HTopic(
            run_id=run_id,
            n_docs=ndocs,
            n_words=nwords,
            scale=scale
        )
        t.save()
        topic['db_id'] = t.topic

    for topic in topics:
        t = HTopic.objects.get(topic=topic['db_id'])
        parent_id = topic['parent']
        if int(parent_id) > -1:         
            for tt in topics: 
                if tt['id'] == parent_id:
                    topic['parent_db_id'] = tt['db_id']
                    break        
            t.parent = HTopic.objects.get(topic=topic['parent_db_id'])
        t.save()

    # Add topicTerm
    tt = state[1]
    for topic_id in range(len(tt)):
        topic = topics[topic_id]
        for term_id in range(len(tt[topic_id])):
            term = terms[term_id]
            if tt[topic_id][term_id] > 0:
                topicterm = HTopicTerm(
                    topic = HTopic.objects.get(topic=topic['db_id']),
                    term = Term.objects.get(term=term['db_id']),
                    count = tt[topic_id][term_id],
                    run_id = run_id
                )
                topicterm.save()

    with open(args.file+".assign", "r") as assign:
        for line in assign:
            (doc_id, score, path) = line.split(None, 2)
            doc_id = int(doc_id)
            doc = docs[doc_id]
            try:
                d = Doc.objects.get(UT=doc)
            except:
                d = Doc(UT=doc)
                d.save()
            score = float(score)
            path = [int(x) for x in path.split()]
            level = -1
            for topic_id in path:
                level+=1
                for topic in topics:
                    if int(topic['id']) == topic_id:
                        t = HTopic.objects.get(topic=topic['db_id'])
                        dt = HDocTopic(
                            doc=d,
                            topic=t,
                            level=level,
                            score=score,
                            run_id=run_id
                        )
                        dt.save()
                        break
                            
                            
            

    # Add doctopics
        

        


# Parse the arguments
parser = argparse.ArgumentParser(description='Update hlda output to the tmv app')
parser.add_argument('file',type=str,help='name of mode or iteration file containing the hlda output')
parser.add_argument('dmap',type=str,help='name of docmap')
parser.add_argument('vocab',type=str,help='name of vocab')

args=parser.parse_args()

if __name__ == '__main__':
    t0 = time.time()
    main(args.file, args.dmap, args.vocab)
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = int(totalTime-(tm*60))

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")

