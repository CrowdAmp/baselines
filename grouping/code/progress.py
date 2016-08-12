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
import numpy as np
import random
import logging

def import_data(subreddits, limit):
    conn = sqlite3.connect('../database.sqlite')
    curs = conn.cursor()

    X = []
    y = []

    for s in subreddits:
        data = curs.execute('select * from May2015 where subreddit="'+s+'" limit '+str(limit)+';')
        for row in data:
            x = row[17]
            x = x.encode('ascii', 'ignore').decode('ascii')
            x = re.sub("[^a-zA-Z]"," ", x)

            X.append(x)
            y.append(subreddits.index(row[8]))

    conn.close()
    return (X, y)

def makeFeatureVec(words, model, num_features):
    # Function to average all of the word vectors in a given
    # paragraph
    #
    # Pre-initialize an empty numpy array (for speed)
    featureVec = np.zeros((num_features,),dtype="float32")
    #
    nwords = 0.
    #
    # Index2word is a list that contains the names of the words in
    # the model's vocabulary. Convert it to a set, for speed
    index2word_set = set(model.index2word)
    #
    # Loop over each word in the review and, if it is in the model's
    # vocaublary, add its feature vector to the total
    for word in words:
        if word in index2word_set:
            nwords = nwords + 1.
            featureVec = np.add(featureVec,model[word])
    #
    # Divide the result by the number of words to get the average
    if nwords != 0:
        featureVec = np.divide(featureVec,nwords)

    return featureVec


def getAvgFeatureVecs(reviews, model, num_features):
    # Given a set of reviews (each one a list of words), calculate
    # the average feature vector for each one and return a 2D numpy array
    #
    # Initialize a counter
    counter = 0.
    #
    # Preallocate a 2D numpy array, for speed
    reviewFeatureVecs = np.zeros((len(reviews),num_features),dtype="float32")
    #
    # Loop through the reviews
    for review in reviews:
       #
       # Print a status message every 1000th review
       if counter%1000. == 0.:
           print "Review %d of %d" % (counter, len(reviews))
       #
       # Call the function (defined above) that makes average feature vectors
       reviewFeatureVecs[counter] = makeFeatureVec(review, model, \
           num_features)
       #
       # Increment the counter
       counter = counter + 1.
    return reviewFeatureVecs

def create_classifier(subreddits, X_train, y_train, num_features):

    # nltk.download()  # Download text data sets, including stop words

    clean_train_set = []

    print "Cleaning and parsing the training set...\n"
    for i in xrange(0, len(X_train)):
        clean_train_set.append(KaggleWord2VecUtility.review_to_wordlist(X_train[i], True))

     # ****** Set parameters and train the word2vec model
    #
    # Import the built-in logging module and configure it so that Word2Vec
    # creates nice output messages
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',\
        level=logging.INFO)

    # Set values for various parameters
    # num_features, min_word_count, num_workers = options

    # num_features = 300    # Word vector dimensionality
    min_word_count = 40   # Minimum word count
    num_workers = 4       # Number of threads to run in parallel
    context = 10          # Context window size
    downsampling = 1e-3   # Downsample setting for frequent words

    # Initialize and train the model (this will take some time)
    print "Training Word2Vec model..."
    model = Word2Vec(clean_train_set, workers=num_workers, \
                size=num_features, min_count = min_word_count, \
                window = context, sample = downsampling, seed=1)

    # If you don't plan to train the model any further, calling
    # init_sims will make the model much more memory-efficient.
    model.init_sims(replace=True)

    # It can be helpful to create a meaningful model name and
    # save the model for later use. You can load it later using Word2Vec.load()
    model_name = "300features_40minwords_10context"
    model.save(model_name)

    print "Creating average feature vecs for training comments"

    train_data_features = getAvgFeatureVecs( clean_train_set, model, num_features )

    print "Training the model (this may take a while)..."

    classifier = LogisticRegression( solver='lbfgs', multi_class='multinomial')
    classifier = classifier.fit(train_data_features, y_train)

    return (model, classifier)

def test_classifier(model, classifier, subreddits, X_test, y_test, num_features):
    # Create an empty list and append the clean reviews one by one
    clean_test_set = []

    print "Cleaning and parsing the test set ...\n"
    for i in xrange(0, len(X_test)):
        clean_test_set.append(KaggleWord2VecUtility.review_to_wordlist(X_test[i], True))

    # Get a bag of words for the test set, and convert to a numpy array
    test_data_features = getAvgFeatureVecs( clean_test_set, model, num_features )

    # Use the random forest to make sentiment label predictions
    print "Predicting test labels...\n"

    predicted = classifier.predict(test_data_features)

    print metrics.accuracy_score(y_test, predicted)
    # print metrics.confusion_matrix(y_test, predicted)
    print metrics.classification_report(y_test, predicted)

def create_vectorizer():
    # Initialize the "CountVectorizer" object, which is scikit-learn's
    # bag of words tool.
    vectorizer = CountVectorizer(analyzer = "word", tokenizer = None, preprocessor = None, \
                                    stop_words = None, max_features = None)
    return vectorizer

if __name__ == '__main__':
    subreddits = ["AskReddit", "videos", "funny", "pics", "gifs", "WTF", "nfl" , "nba", "aww", "technology", "movies", "Fallout", "Bitcoin" "gaming", "politics", "Music"]
    
    X, y = import_data(subreddits, 1000)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    num_features = 300 

    model, classifier = create_classifier(subreddits, X_train, y_train, num_features)
    test_classifier(model, classifier, subreddits, X_test, y_test, num_features)

    
         








