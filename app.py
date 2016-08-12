import os
import psycopg2
import urlparse
from flask import Flask
import pickle
from sklearn.externals import joblib
from sklearn import svm
import numpy

app = Flask(__name__)

#Global SVM
clf = None


def train(X, y, c, g):
	global clf
	clf = svm.SVC(C = c, gamma = g)
	clf.fit(X,y)
	print 'finished training svm'
	return clf

def test(X):
	global clf
	predictions = clf.predict(X)
	print 'finished predicting'
	return predictions

################################ 
# Feature Functions
###############################

def wordOverlap(s1, s2):
	overlap = 0
	s1_tokenize = s1.split()
	s2_tokenize = s2.split()
	used_array = []
	for token in s1_tokenize:
		if token in s2_tokenize:
			if token not in used_array:
				overlap += 1
				used_array.append(token)
	return overlap

def jaccard(sentence1, sentence2):
	s1_tokenize = sentence1.split()
	s2_tokenize = sentence2.split()
	s1_set = set(s1_tokenize)
	s2_set = set(s2_tokenize)
    #print s1_set.intersection(s2_set)
    #print s1_set.union(s2_set)
	return float(len(s1_set.intersection(s2_set)))/float(len(s1_set.union(s2_set)))

question_words = ["who", "what", "when", "where", "why", "how"]
def qwordIndicator(s1, s2):
	s1_tokenize = s1.split()
	s2_tokenize = s2.split()
	s1_set = set(s1_tokenize)
	s2_set = set(s2_tokenize)
	for word in question_words:
		if word in s1_set.intersection(s2_set):
			return 1
        
	return 0


def bigramOverlap(s1, s2):
	s1_tokenize = s1.split()
	s2_tokenize = s2.split()
	bigram_overlap = 0
	s1_bigrams = set([(s1_tokenize[i], s1_tokenize[i+1]) for i in range(0, len(s1_tokenize)-1)])
	s2_bigrams = set([(s2_tokenize[i], s2_tokenize[i+1]) for i in range(0, len(s2_tokenize)-1)])
	bigram_overlap = len(s1_bigrams.intersection(s2_bigrams))
	return bigram_overlap


def bigramJaccard(s1, s2):
	s1_tokenize = s1.split()
	s2_tokenize = s2.split()
	bigram_overlap = 0
	s1_bigrams = set([(s1_tokenize[i], s1_tokenize[i+1]) for i in range(0, len(s1_tokenize)-1)])
	s2_bigrams = set([(s2_tokenize[i], s2_tokenize[i+1]) for i in range(0, len(s2_tokenize)-1)])
	return float(len(s1_bigrams.intersection(s2_bigrams)))/float(len(s1_bigrams.union(s2_bigrams)))


####################################
# Create feature vector from two strings
#######################################
def buildFeatureVector(s1, s2):
	wo = wordOverlap(s1, s2)
	ujaccard = jaccard(s1, s2)
	qword = qwordIndicator(s1, s2)
	bi = bigramOverlap(s1, s2)
	bijaccard = bigramJaccard(s1, s2)
	arr = [wo, ujaccard, qword, bi, bijaccard]
	return arr

############################### 
# Requests
##############################

@app.route('/storeq')
def storeQuestions():
    # Add to 'new questions' file?
    return 'storing question'


@app.route('/sameq')
def sameQuestions():
    # create vector from two strings as X value
	testString1 = "how many days are in the week"
	testString2 = "the week has many days"
	x = buildFeatureVector(testString1, testString2)
    # make 0 or 1 prediction
	X = [x]
	prediction = test(X)
	return str(prediction[0])


@app.route('/')
def startSVM():
	global clf
	clf = joblib.load('trainedquestionsvm.pkl')
	return 'Successfully loaded svm'

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
	port = int(os.environ.get('PORT', 5000))
	app.run(host='0.0.0.0', port=port)

