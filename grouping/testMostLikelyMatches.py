glove_home = "../../cs224u/glove.6B"

import psycopg2
import random
import numpy as np
from requests import get
from nltk.stem import WordNetLemmatizer
import os
import sys
import unicodecsv as csv
import random
import itertools
from operator import itemgetter
from collections import defaultdict
import scipy
import scipy.spatial.distance
import utils


sss_url = "http://swoogle.umbc.edu/SimService/GetSimilarity"
sts_url = "http://swoogle.umbc.edu/StsService/GetStsSim"

def sss(s1, s2, url, type='relation', corpus='webbase'):
    try:
        response = get(url, params={'operation':'api','phrase1':s1,'phrase2':s2,'type':type,'corpus':corpus})
        return float(response.text.strip())
    except:
        print 'Error in getting similarity for %s: %s' % ((s1,s2), response)
        return 0.0

def sts(s1, s2, url):
    try:
        response = get(url, params={'operation':'api','phrase1':s1,'phrase2':s2})
        return float(response.text.strip())
    except:
        print 'Error in getting similarity for %s: %s' % ((s1,s2), response)
        return 0.0

#val1 = sss('a small violin is being played by a girl', 'a child is performing on a tiny instrument', sss_url, type='concept')
#print val1


#val3 = sts('a small violin is being played by a girl', 'a child is performing on a tiny instrument', sts_url)
#print val3

#print 'Loading glove vectors\n'
#glv_src = os.path.join(glove_home, 'glove.6B.50d.txt')
#glv = utils.build_glove(os.path.join(glove_home, 'glove.6B.50d.txt'))
#print 'Finished building glove vectors\n'

def cosine(u, v):
    """Cosine distance between 1d np.arrays `u` and `v`, which must have 
    the same dimensionality. Returns a float."""
    # Use scipy's method:
    return scipy.spatial.distance.cosine(u, v)


#def distance_between_sentences(str1, str2, mat = glv[0], rownames = glv[1], distfunc = cosine):
#	str1_list = str1.split()
#	str2_list = str2.split()

#	str1_vecs = [mat[rownames.index(word)] for word in str1_list if word in rownames]
#	str2_vecs = [mat[rownames.index(word)] for word in str2_list if word in rownames]
#	str1_rand_vecs = [utils.randvec(50) for word in str1_list if word not in rownames]
#	str2_rand_vecs = [utils.randvec(50) for word in str2_list if word not in rownames]

#	str1_combined_vecs = 0
#	str2_combined_vecs = 0

#	for vec in str1_vecs:
#		str1_combined_vecs += vec
#	for vec in str1_rand_vecs:
#		str1_combined_vecs += vec

#	for vec in str2_vecs:
#		str2_combined_vecs += vec
#	for vec in str2_rand_vecs:
#		str2_combined_vecs += vec

#	return distfunc(str1_combined_vecs, str2_combined_vecs)


def getMatches(conn, cur, influencerid, messageContent):
	#lemmatizer = WordNetLemmatizer()
	#messageContent = "I am your biggest fan"
	#tokenized = messageContent.split()
	#for word in tokenized:
		#print lemmatizer.lemmatize(word)
		#print "stemmed word " + word
	#influencerid = 1
	#conn = psycopg2.connect(
    	#database="d8p14gpjl2i8a",
    	#user="hxlockbodckoio",
    	#password="1a32xeqTaKHl_1HE2S9HPN2Vw-",
    	#host="ec2-54-235-240-76.compute-1.amazonaws.com",
    	#port=5432
	#)
	#cur = conn.cursor()
	queryStr = "SELECT * FROM phraseids WHERE influencerid = '" + influencerid + "' AND catchallcategory = 'N' ORDER BY id;"
	cur.execute(queryStr)
	conn.commit()
	
	dbdata = cur.fetchall()
	#similarities = []
	#for row in dbdata:
		#sss_val = sss('hi', 'hi', sss_url, type='relation')
		#sts_val = sts(messageContent, row[1], sts_url)
		#dist = distance_between_sentences(messageContent, row[1])
		#similarities.append(dist)
	#similarities = np.array(similarities)
	#topfive = similarities.argsort()[:5]
	#print topfive
	#closestPhrases = [dbdata[index] for index in topfive]
	return dbdata
	#conn.close()

#getMatches(1,1,1,1)
sentence1 = "hi I love you more than my mom"
sentence2 = "Yo you are my favorite"
sentence3 = "you are my favorite"
sentence4 = "hi I hate you so much"
sentence5 = "asdfkakjdfhkasdjfhaksjdh"
sentence6 = "Your face is on fire"

#print 'Difference between ' + sentence1 + ' and ' + sentence4
#print distance_between_sentences(sentence1, sentence4)

#print 'Difference between ' + sentence1 + ' and ' + sentence5
#print distance_between_sentences(sentence5, sentence1)

#print 'Difference between ' + sentence1 + ' and ' + sentence6
#print distance_between_sentences(sentence1, sentence6)
#GLOVE50 = utils.glove2dict(glv_src)

#for word in sentence1:
	#w = unicode(word, "utf-8")
	#vec = GLOVE50.get(w, utils.randvec(50))
	#print vec


#print 'finished glove vectorizing'
