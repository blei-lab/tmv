#!/usr/bin/env python3

# onlinewikipedia.py: Demonstrates the use of online VB for LDA to
# analyze a bunch of random Wikipedia articles.
#
# Copyright (C) 2010  Matthew D. Hoffman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
sys.stdout.flush()

# import file for easy access to browser database
sys.path.append('/home/galm/software/tmv/BasicBrowser/')

# sys.path.append('/home/max/Desktop/django/BasicBrowser/')
import db3 as db

def iter_docs(texts, stoplist):
	for text in texts:
		yield (x for x in 
			gensim.utils.tokenize(text, lowercase=True, deacc=True, 
                                  errors="ignore")
			if x not in stoplist and len(x) > 2)

class MyCorpus(object):
	def __init__(self, texts, stoplist):
		self.texts = texts
		self.stoplist = stoplist
		self.dictionary = gensim.corpora.Dictionary(iter_docs(texts, stoplist))

	def __iter__(self):
		for tokens in iter_docs(self.texts, self.stoplist):
			yield self.dictionary.doc2bow(tokens)

class MiniCorpus(object):
	def __init__(self, texts, stoplist,dictionary):
		self.texts = texts
		self.stoplist = stoplist
		self.dictionary = dictionary

	def __iter__(self):
		for tokens in iter_docs(self.texts, self.stoplist):
			yield self.dictionary.doc2bow(tokens)


def main():

	

	print("starting topic model - about to read WoS results")
	#df = scrapeWoS.readWoS('../query/results.txt')
	df = scrapeWoS.readWoS('results.txt')
	# filter articles with missing abstracts, and only include articles and reviews
	df = df[(pd.notnull(df.AB)) & (pd.notnull(df.UT)) & (df.DT.isin(["Article","Review"]))].reset_index()

	# Randomly reorder (or take a sample) the docs
	df = df.sample(frac=0.1).reset_index(drop=True)

	print("found "+str(len(df))+ " articles")
	sys.stdout.flush()


	df.IN = df.index.tolist()

	# The number of documents to analyze each iteration
	batchsize = 100
	# The total number of documents in Wikipedia
	D = len(df)
	documentstoanalyze = int(D)
	iterations = D//batchsize
	# The number of topics
	try:
		K = int(sys.argv[1])
		print(K)
	except:
		K = 100
	

	docset = list(df.AB)

#	####### making a corpus
	stoplist = set(nltk.corpus.stopwords.words("english"))
	stoplist.add('Elsevier')

	mycorpus = MyCorpus(docset,stoplist)

	dictionary = mycorpus.dictionary#.filter_extremes(no_below=5, no_above=0.9)

	dictionary.filter_extremes(no_below=5, no_above=0.9)

	x = list(dictionary.values())
	y = list(dictionary)


	vocab = sorted(zip(y,x))

	W = len(vocab)

	print("found " + str(W) + " terms")

	sys.stdout.flush()

	run_id = db.init()

	# add terms to db

	db.add_terms(vocab)

	# add empty topics to db
	db.add_topics(K)
#	for k in range(K):
#		db.add_topic(k)

	# add all docs
	def f_doc(d):
		django.db.connections.close_all()
		db.add_doc(d[0],d[1],d[2],d[3],d[4],d[5])
		django.db.connections.close_all()

	def f_gamma(d):
		django.db.connections.close_all()
		doc_size = len(docset[d])
		doc_id = iteration*100+d+doc_diff
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

	# Take the information we need from the doc list then delete to free up memory
	docs = zip(df.TI,df.AB,df.IN,df.UT,df.PY,df.AU)
	all_docs = list(df.AB)

	# Add the documents to the database
	print("Adding docs to database")
	pool = Pool(processes=8)
	pool.map(f_doc, docs)
	pool.terminate()

	global doc_diff
	doc_diff = db.docdiff(df.IN[-1])
	del(df)


	del(docs)
	gc.collect()

#	docs = zip(df.TI,df.AB,df.IN,df.UT,df.PY,df.AU)

#	pool = Pool(processes=8)
#	pool.map(f_auth,docs)
#	pool.terminate()

	print("All docs added, initialising topic model")
	olda = gensim.models.LdaMulticore(num_topics=K,id2word=dictionary,workers=8)

	# Run until we've seen D documents. (Feel free to interrupt *much*
	# sooner than this.)
	for iteration in range(0, iterations):
		t0 = time.time()	
		firstDoc = batchsize*iteration
		lastDoc = batchsize*(iteration+1)
		if lastDoc > D:
			lastDoc = D
      
		docset = all_docs[firstDoc:lastDoc]

		mycorpus = MiniCorpus(docset,stoplist,dictionary)
		
		olda_t0 = time.time()	
		olda.update(mycorpus)
		elapsed = time.time() - t0

		print("updated with docs "+str(firstDoc)+" to " + str(lastDoc)+": took "+str(elapsed))

		# Get the gamma (doc-topic matrix) and add to database
		gamma = olda.inference(mycorpus)

		gamma = gamma[0]
	
		docs = range(len(gamma))

		pool = Pool(processes=8)
		pool.map(f_gamma,docs)
		pool.terminate()

		# Every 10th iteration, get the lambda (topic-term matrix) and add to database
		if (iteration % 20 == 0):

			ldalambda = olda.inference(mycorpus,collect_sstats=True)[1]
			numpy.savetxt('lambda-%d.dat' % iteration, ldalambda)
			numpy.savetxt('gamma-%d.dat' % iteration, gamma)			
			
			topics = range(len(ldalambda))

			pool = Pool(processes=8)
			pool.map(f_lambda,topics)
			pool.terminate()

		gc.collect() 
		sys.stdout.flush()
		elapsed = time.time() - t0
		print(elapsed)
		db.increment_batch_count()

	olda.save("olda"+str(run_id))

if __name__ == '__main__':
	t0 = time.time()	
	main()
	totalTime = time.time() - t0

	tm = int(totalTime//60)
	ts = int(totalTime-(tm*60))

	print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
