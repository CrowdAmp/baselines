import os
import sqlite3
import nltk
import re
import csv
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cross_validation import train_test_split
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from KaggleWord2VecUtility import KaggleWord2VecUtility
from gensim.models import Word2Vec
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation, Masking
from keras.layers.embeddings import Embedding
from keras.layers.recurrent import GRU, LSTM
from keras.utils import np_utils
import numpy as np
import random
import logging
import argparse
import sys
import pickle

num_features = 300
batch_size = 32


########################################################
######################## MODELS ########################
########################################################


def redditWordVectors(X):	
	min_word_count = 40   # Minimum word count
	num_workers = 6       # Number of threads to run in parallel
	context = 10          # Context window size
	downsampling = 1e-3   # Downsample setting for frequent words

	print "Training Word2Vec model..."
	model = Word2Vec(X, workers=num_workers, \
				size=num_features, min_count = min_word_count, \
				window = context, sample = downsampling, seed=1)

	# # If you don't plan to train the model any further, calling
	# # init_sims will make the model much more memory-efficient.
	model.init_sims(replace=True)
	return model

def bagOfWords(X):
	# Initialize the "CountVectorizer" object, which is scikit-learn's
    # bag of words tool.
    vectorizer = CountVectorizer(analyzer = "word",   
	                             tokenizer = None,    
	                             preprocessor = None, 
	                             stop_words = None,   
	                             max_features = 5000)

    # Fit the bag of words model to the vocabulay of X
    vectorizer.fit(X)
    return vectorizer


def makeFeatureVec(words, model, index2word_set, num_features):
	# Function to average all of the word vectors in a given
	# paragraph
	
	# Pre-initialize an empty numpy array (for speed)
	featureVec = np.zeros((num_features,), dtype="float32")
	nwords = 0
	
	# Loop over each word in the review and, if it is in the model's
	# vocaublary, add its feature vector to the total
	for word in words:
		if word in index2word_set:
			nwords = nwords + 1
			featureVec = np.add(featureVec, model[word])

	# Divide the result by the number of words to get the average
	if nwords != 0:
		featureVec = np.divide(featureVec, nwords)

	return featureVec
	
def getAvgFeatureVecs(reviews, model, num_features):
	# Given a set of reviews (each one a list of words), calculate
	# the average feature vector for each one and return a 2D numpy array
	counter = 0
	
	reviewFeatureVecs = np.zeros((len(reviews), num_features),dtype="float32")
	index2word_set = set(model.index2word)
	# Loop through the reviews
	for review in reviews:

	   if counter % 100 == 0:
		   print "Review %d of %d" % (counter, len(reviews))
	
	   reviewFeatureVecs[counter] = makeFeatureVec(review, model, index2word_set, num_features)
	   counter = counter + 1

	return reviewFeatureVecs

def getEmbeddingMatrix(words, model, vocab, max_comment_length):
	featureVec = np.zeros((max_comment_length,num_features))
	idx = 0
	for word in words:
		if idx >= max_comment_length:
			break
		if word in vocab:
			featureVec[-(idx + 1)] = model[word]
			idx += 1
	return featureVec

def getWordEmbeddings(comments, model, max_comment_length):
	wordIndexVecs = np.zeros((len(comments),max_comment_length, num_features))
	vocab = set(model.index2word)
	for counter, comment in enumerate(comments):
		if counter%1000. == 0.:
		   print "Comment %d of %d" % (counter, len(comments))
		wordIndexVecs[counter] = getEmbeddingMatrix(comment, model, vocab, max_comment_length)
	return wordIndexVecs

############################################################
######################## ALGORITHMS ########################
############################################################

def create_lr_classifier(model, num_features, X_train, y_train):

	print "Creating average feature vecs for training comments"
	train_data_features = getAvgFeatureVecs(X_train, model, num_features)

	print "Training classifier model (this may take a while)..."
	classifier = LogisticRegression( solver='lbfgs', multi_class='multinomial')
	classifier = classifier.fit(train_data_features, y_train)

	return classifier

def create_bw_lr_classifier(model, X_train, y_train):

	print "Creating bag of feature vecs for training comments"
	train_data_features = model.transform(X_train)
	train_data_features.toarray()

	print "Training classifier model (this may take a while)..."
	classifier = LogisticRegression( solver='lbfgs', multi_class='multinomial')
	classifier = classifier.fit(train_data_features, y_train)

	return classifier


def create_nn_classifier(model, num_features, X_train, y_train, num_classes):
	hidden_layer_size = 200
	max_seq_length = 100
	nb_epoch = 5

	print "Creating word embedding vecs for training comments"
	train_data_features = getWordEmbeddings(X_train, model, max_seq_length)

	print "Training the model (this may take a while)..."
	classifier = Sequential()
	M = Masking(mask_value=0)
	M._input_shape = (1,max_seq_length,num_features)
	classifier.add(M)
	classifier.add(GRU(output_dim=hidden_layer_size, input_dim=num_features, return_sequences=False))
	classifier.add(Dropout(0.5))
	classifier.add(Dense(num_classes, init='glorot_normal'))
	classifier.add(Activation('softmax'))

	# optimizer = Adam(clipnorm=10)

	classifier.compile(loss='categorical_crossentropy', optimizer='adam')

	classifier.fit(train_data_features, y_train, nb_epoch=nb_epoch, batch_size=batch_size, verbose=1, show_accuracy=True, validation_split=0.1)

	return classifier


def test_lr_classifier(model, classifier, X_test, y_test, num_features):

	test_data_features = getAvgFeatureVecs(X_test, model, num_features)

	print "Predicting test labels...\n"
	predicted = classifier.predict(test_data_features)

	print metrics.accuracy_score(y_test, predicted)
	# print metrics.confusion_matrix(y_test, predicted)
	print metrics.classification_report(y_test, predicted)


def test_bw_lr_classifier(model, classifier, X_test, y_test):

	test_data_features = model.transform(X_test)
	test_data_features = test_data_features.toarray()

	print "Predicting test labels...\n"
	predicted = classifier.predict(test_data_features)

	print metrics.accuracy_score(y_test, predicted)
	# print metrics.confusion_matrix(y_test, predicted)
	print metrics.classification_report(y_test, predicted)

def test_nn_classifier(model, classifier, X_test, y_test, num_features):

	test_data_features = getWordEmbeddings(X_test, model, num_features)

	print "Predicting test labels...\n"
	predicted = classifier.predict_classes(test_data_features, batch_size=batch_size, verbose=1)

	print metrics.accuracy_score(y_test, predicted)
	# print metrics.confusion_matrix(y_test, predicted)
	print metrics.classification_report(y_test, predicted)


############################################################
########################## SCRIPT ##########################
############################################################

def exit_with_error(error):
	print error
	quit()

def importData(datafile, subreddits, limit, model):

	# nltk.download()  # Download text data sets, including stop words
	conn = sqlite3.connect(datafile)
	curs = conn.cursor()

	X = []
	y = []
	for s in subreddits:
		print "Subreddit:", s
		data = curs.execute('select * from May2015 where subreddit="'+s+'" limit '+str(limit)+';')
		for idx, row in enumerate(data):
			x = row[17]
			x = x.encode('ascii', 'ignore').decode('ascii')
			x = re.sub("[^a-zA-Z']"," ", x)
			x = KaggleWord2VecUtility.review_to_wordlist(x, False)
			if model == "bw":
				x = " ".join(x)

			X.append(x)
			y.append(subreddits.index(row[8]))
			if idx % 1000 == 999:
				print "Imported comment ", idx + 1

	conn.close()
	return (X, y)

def getRandomSubreddits(count):
	all_subreddits = ['gifs', 'explainlikeimfive', 'science', 'nba', 'politics', 'gaming', 'news', 
	'StarWars', 'funny', 'AskReddit', 'soccer', 'technology', 'todayilearned', 'Fitness', 'aww', 
	'books', 'food', 'askscience', 'Showerthoughts', 'atheism', 'Music', 'space', 'Fallout', 
	'worldnews', 'IAmA', 'pics', 'Jokes', 'videos', 'trees', 'WTF'] 

	if count > len(all_subreddits):
		count = len(all_subreddits)

	return random.sample(all_subreddits, count)

def usage():
	return "Usage: final.py\n\
			-s <# subreddits>\n\
			-n <# max comments per subreddit>\n\
			-r <random seed>\n\
			-m <model: 'wv', 'gwv', 'bw'>\n\
			-i <input file for model>\n\
			-c <classifier: 'nn', 'lr'>\n\
			<database>.sqlite"


if __name__ == '__main__':


	if len(sys.argv) < 2:
		print "Type 'python final.py help' for help"
		exit_with_error(usage())


	parser = argparse.ArgumentParser()
	parser.add_argument("-s", "--s", default=None)	# Number of subreddits
	parser.add_argument("-n", "--n", default=1000)	# Number of max comments per subreddit
	parser.add_argument("-r", "--r", default=1) 	# Random seed
	parser.add_argument("-i", "--i", default=None)	# Input file (if loading model)
	
	# Which model to use? Word2Vec 'wv', GoogleWord2Vec 'gwv', BagOfWords 'bw' 
	parser.add_argument("-m", "--m", default="") 	

	# Which classifier to use? RNN 'nn' or Logistic Regression 'lr'
	parser.add_argument("-c", "--c", default="nn")	
	
	parser.add_argument("datafile", nargs=1)
	args = parser.parse_args()

	random.seed(int(args.r))

	if args.c != 'nn' and args.c != 'lr':
		exit_with_error("classifier not recognized: " + args.c)

	# If the user has specified a value for s, pick s random subreddits.
	if args.s:
		subreddits = getRandomSubreddits(int(args.s))
	else:
		subreddits = ["aww", "technology", "movies", "Bitcoin", "gaming", "politics", "Music"]
	
	print "Selected subreddits: ", subreddits

	X, y = importData(args.datafile[0], subreddits, int(args.n), args.m)

	X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

	##
	## CONSTRUCT/SAVE OR LOAD MODEL
	## 

	logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

	# If we are given an input file, load it
	if args.i:
		if args.m == "wv":		# Word2Vecs
			model = Word2Vec.load(args.i)
		elif args.m == "bw":	# Bag of words
			model = pickle.load(open(args.i, "rb"))
		elif args.m == "gwv": 	# Google Word2Vecs
			model = Word2Vec.load_word2vec_format(args.i, binary=True)
		else:
			exit_with_error("Input file given, but model not recognized")

	# Otherise, construct a new model and save it
	elif args.m == "wv":
		model = redditWordVectors(X)
		model_name = "300features_40minwords_10context_" + str(len(X)) + "comments"
		model.save(model_name)
		print "Model saved as", model_name

	elif args.m == "bw":
		model = bagOfWords(X)
		model_name = "bagOfWords_" + str(len(X)) + "comments"
		pickle.dump(model, open(model_name, "wb" ))
		print "Model saved as", model_name
	
	else:
		exit_with_error("Model not recognized")

	##
	## CREATE AND TEST CLASSIFIER
	## 

	if args.m == "bw":
		classifier = create_bw_lr_classifier(model, X_train, y_train)
		test_bw_lr_classifier(model, classifier, X_test, y_test)

	elif args.c == "nn":
		_y_train = np_utils.to_categorical(y_train, len(subreddits))
		classifier = create_nn_classifier(model, num_features, X_train, _y_train, len(subreddits))
		test_nn_classifier(model, classifier, X_test, y_test, num_features)

	elif args.c == "lr":
		classifier = create_lr_classifier(model, num_features, X_train, y_train)
		test_lr_classifier(model, classifier, X_test, y_test, num_features)

	print "Subreddits: ", subreddits
