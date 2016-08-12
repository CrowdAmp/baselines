from sklearn.externals import joblib
from sklearn import svm
import os
import sys
import unicodecsv as csv
import random
import itertools
from operator import itemgetter
from collections import defaultdict
import numpy as np
import scipy
import scipy.spatial.distance
from numpy.linalg import svd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import utils
import numpy
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.cross_validation import train_test_split

def train(X, y,c, g):
    clf = svm.SVC(C = c, gamma = g)
    clf.fit(X,y)
    print 'finished training svm'
    return clf

def test(clf, X):
    predictions = clf.predict(X)
    print 'finished predicting'
    return predictions

clf = joblib.load('trainedquestionsvm.pkl') 

print 'successfully imported svm'
