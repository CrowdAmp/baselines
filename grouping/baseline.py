import os
import psycopg2
import nltk
import re
import csv
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cross_validation import train_test_split
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
from KaggleWord2VecUtility import KaggleWord2VecUtility
import numpy as np
import random


#  id  | phrase                  |  influencerid   |    userid    |          timesent          | context | messagetype | sentbyuser | phrasegroup |                                                                                  mediaurl                                                                                   | numtimesresponded | conversationid 

def executeDBCommand(conn, cur, query):
    cur.execute(query)
    conn.commit()

def baseline(subreddits):
    #conn = sqlite3.connect('../database.sqlite')
    #curs = conn.cursor()
    conn = psycopg2.connect(
        database="d1jfg4556jcg85",
        user="u95kuk1lu5e68c",
        password="p9462kijpsfllp2i03nc3bqq6gt",
        host="ec2-52-204-179-136.compute-1.amazonaws.com",
        port=5432
    )
    cur = conn.cursor()
    # select values that are not 'uncategorized' or grouped into a single message
    queryStr = "SELECT * FROM unprocessedmessages WHERE id != -1 AND id != 24 and sentbyuser = 'True';"
    executeDBCommand(conn, cur, queryStr)
    data = cur.fetchall()
    # index 1 -- phrase
    #
    # for row in data:
	# row[1] -- phrase (X)
	# row[8] -- categorized (y) 
    X = []
    y = []

    #for s in subreddits:
        #data = curs.execute('select * from May2015 where subreddit="'+s+'" limit 33;')
        #for row in data:
            #x = row[17]
            #x = x.encode('ascii', 'ignore').decode('ascii')
            #x = re.sub("[^a-zA-Z]"," ", x)

            #X.append(x)
            #y.append(row[8])

    conn.close()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    
    print 'The first comment is:'
    print X_train[0]
    raw_input("Press Enter to continue...")


    # print 'Download text data sets. If you already have NLTK datasets downloaded, just close the Python download window...'
    # nltk.download()  # Download text data sets, including stop words

    # Initialize an empty list to hold the clean comments
    clean_train_set = []

    # Loop over each body; create an index i that goes from 0 to the length
    # of the list

    print "Cleaning and parsing the training set...\n"
    for i in xrange(0, len(X_train)):
        clean_train_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_train[i], False)))

    print 'The new first comment is:'
    print clean_train_set[0]
    raw_input("Press Enter to continue...")

    # ****** Create a bag of words from the training set
    #
    print "Creating the bag of words...\n"


    # Initialize the "CountVectorizer" object, which is scikit-learn's
    # bag of words tool.
    vectorizer = CountVectorizer(analyzer = "word",   \
                             tokenizer = None,    \
                             preprocessor = None, \
                             stop_words = None,   \
                             max_features = 5000)

    # fit_transform() does two functions: First, it fits the model
    # and learns the vocabulary; second, it transforms our training data
    # into feature vectors. The input to fit_transform should be a list of
    # strings.
    train_data_features = vectorizer.fit_transform(clean_train_set)

    # Numpy arrays are easy to work with, so convert the result to an
    # array
    train_data_features = train_data_features.toarray()

    # ******* Train Model
    #
    print "Training the model (this may take a while)..."

    model = LogisticRegression( solver='lbfgs', multi_class='multinomial')
    model = model.fit(train_data_features, y_train)

    # Create an empty list and append the clean reviews one by one
    clean_test_set = []

    print "Cleaning and parsing the test set ...\n"
    for i in xrange(0, len(X_test)):
        clean_test_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_test[i], False)))

    # Get a bag of words for the test set, and convert to a numpy array
    test_data_features = vectorizer.transform(clean_test_set)
    test_data_features = test_data_features.toarray()

    # Use the random forest to make sentiment label predictions
    print "Predicting test labels...\n"

    predicted = model.predict(test_data_features)

    print metrics.accuracy_score(y_test, predicted)
    # print metrics.confusion_matrix(y_test, predicted)
    print metrics.classification_report(y_test, predicted)

def oracle(subreddits):
    # # Copy the results to a pandas dataframe with an "id" column and
    # # a "subreddit" column
    # output = pd.DataFrame( data={"body":X_test, "predicted_subreddit":predicted, "actual_subreddit":y_test} )
    # # # Use pandas to write the comma-separated output file
    # output.to_csv(os.path.join(os.path.dirname(__file__), 'data', 'prediction.csv'), index=False, quoting=csv.QUOTE_NONE, quotechar='', escapechar='\\')
    # print "Wrote results to prediction.csv"

    raw_input("Now performing Oracle. Press Enter to continue...")
    num_iterations = 30
    X = []
    Y = []
    conn = sqlite3.connect('../database.sqlite')
    curs = conn.cursor()

    for s in subreddits:
        print s
        for row in curs.execute('select * from May2015 where subreddit="'+s+'" limit 100;'):
            curs2 = conn.cursor()
            other_comments_data = curs2.execute('select * from May2015 where link_id="'+row[3]+'" limit 3;')
            other_comments = []
            for row2 in other_comments_data:
                other_comments.append(row2[17])

            X.append((row[17], other_comments))
            Y.append(row[8])

    indexes = range(len(X))
    random.shuffle(indexes)
    predicted = []

    for i in range(num_iterations):
        idx = indexes[i]
        x = X[idx]
        print "========================"
        print "Comment: ", x[0]
        for c in x[1]:
            if c == x[0]:
                continue
            # print "- ", c

        subreddit = raw_input("Guess: ")
        predicted.append(subreddit)
        print "Correct subreddit:", Y[idx]
        print "========================"


    correct = [Y[indexes[i]] for i in range(num_iterations)]
    print "predicted: ", predicted
    print "correct: ", correct

    print metrics.accuracy_score(correct, predicted)
    print metrics.classification_report(correct, predicted)


if __name__ == '__main__':
    categories = ["gaming", "politics", "Music"]

    baseline(subreddits)
    # oracle(subreddits)

    
         








