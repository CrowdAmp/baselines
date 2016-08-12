import psycopg2
import os
import sys
from testMostLikelyMatches import getMatches
import traceback
from flask import Flask, jsonify, request, json
import requests
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
import urlparse
import pickle
from baseline2 import baseline
from string import punctuation

# Handle grouping, maunally input 5 most common messages

# Undo if mistake

# Send 5 most common messages to influencer
# (i.e. call to influencerDidRespondToPrompt)


# Send responses for top 5 most common messages
# (i.e. call to shouldSendMessageToUsers)

############ 
# Globals
###########
conn = None
cur = None

def executeDBCommand(conn, cur, query):
    cur.execute(query)
    conn.commit()

def promptForInfluencerName():
    influencerName = raw_input("Enter influencerid: ")
    queryStr = "SELECT * FROM influencers WHERE name = '" + influencerName + "';"
    executeDBCommand(conn, cur, queryStr)
    influencer = cur.fetchall()
    if len(influencer) == 0:
        print '\nInvalid influencer name'
        return "-1"
    return influencerName

def promptInfluencer():
    url = 'https://fierce-forest-11519.herokuapp.com/shouldPromptInfluencerForAnswer'
    headers = {'content-type': 'application/json'}
    influencerName = promptForInfluencerName()
    queryStr = "SELECT * from phraseids WHERE influencerid = '" + influencerName + "' AND catchallcategory = 'N' AND prompted = 'N' ORDER BY numusers desc LIMIT 5;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    for row in info:
        phraseid = row[0]
        data = { "phraseId" : str(phraseid) }
        requests.post(url, data=json.dumps(data), headers=headers)
    print 'Influencer has been prompted\n'

def respondToOne(phraseid):
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToUsers'
    headers = {'content-type': 'application/json'}
    data = { "phraseId" : str(phraseid) }
    requests.post(url, data=json.dumps(data), headers=headers)

def sendResponses():
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToUsers'
    headers = {'content-type': 'application/json'}
    influencerName = promptForInfluencerName()
    queryStr = "SELECT * from phraseids WHERE influencerid = '" + influencerName + "' AND catchallcategory = 'N' ORDER BY numusers desc;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    for row in info:
        print "sending response to: " + row[1]
        phraseid = row[0]
        data = { "phraseId" : str(phraseid) }
        requests.post(url, data=json.dumps(data), headers=headers)


# TODO: Enhance NLP Stuffs
def displayTopFive(influencerName, phrase, messageid, otherId):
    global conn
    global cur
    validCategories = [str(i) for i in range(0, 101)]
    dbdata = getMatches(conn, cur, influencerName, phrase)
    if len(dbdata) < 5:
        comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
    else:
        comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
    for i in range(0, len(comparisonPhrases)):
        print str(i) + ': ' + comparisonPhrases[i]
    print '\n'
    categoryText = "-1"
    while categoryText not in validCategories:
        #quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
        categoryText = raw_input("Enter category, 100 if none of the above: ")
        if categoryText == 'q':
            return 'q'
        if categoryText == 'u':
            return 'u'
    index = int(categoryText)
    if index == 100 or index >= len(comparisonPhrases):
        phrasegroupid = otherId
    else:
        phrasegroupid = dbdata[index][0]
    queryStr = "SELECT phrasegroup FROM unprocessedmessages WHERE userid = (SELECT userid from unprocessedmessages WHERE id = " + str(messageid) + ");"
    executeDBCommand(conn, cur, queryStr)
    previousResponses = cur.fetchall()
    previousPhrasegroups = [previousResponses[i][0] for i in range(0, len(previousResponses))]
        #if phrasegroupid in previousPhrasegroups:
        #print "That response has already been used, classifying as other"
        #phrasegroupid = otherId
    queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(phrasegroupid) + " WHERE id = " + str(messageid) + ";"
    executeDBCommand(conn, cur, queryStr)
    queryStr = "UPDATE phraseids SET numusers = numusers + 1 WHERE id = " + str(phrasegroupid) + ";"
    executeDBCommand(conn, cur, queryStr)
    return 0

# Returns id of the uncategorized group    
def getUncategorized(conn, cur, influencerName):
    queryStr = "SELECT id FROM phraseids WHERE phrasecategories = 'uncategorized';"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    if len(info) == 0:
        print 'No uncategorized, creating one now'
        queryStr = "INSERT INTO phraseids VALUES (DEFAULT, 'uncategorized', '" + influencerName+ "', DEFAULT, 'Y', DEFAULT);"
        executeDBCommand(conn, cur, queryStr)
        queryStr = "SELECT id FROM phraseids WHERE influencerid = '" + influencerName + "' AND phrasecategories = 'uncategorized';"
        executeDBCommand(conn, cur, queryStr)
        info = cur.fetchall()
    uncategorizedId = info[0][0]
    return uncategorizedId

# Reutrns the messageid of the other group
def getOtherId(conn, cur, influencerName):
    queryStr = "SELECT id FROM phraseids WHERE influencerid = '" + influencerName + "' AND phrasecategories = 'other';"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    if len(info) == 0:
        print 'No other category, creating one now'
        queryStr = "INSERT INTO phraseids VALUES (DEFAULT, 'other', '" + influencerName+ "', DEFAULT, 'Y', DEFAULT);"
        executeDBCommand(conn, cur, queryStr)
        queryStr = "SELECT id FROM phraseids WHERE influencerid = '" + influencerName + "' AND phrasecategories = 'other';"
        executeDBCommand(conn, cur, queryStr)
        info = cur.fetchall()
    otherId = info[0][0]
    return otherId

# Used to undo classification mistakes
def recategorizePrevious(conn, cur):
    messageid = raw_input("Type message id of phrase to recategorize or q to continue categorizing new phrases: ")
    if messageid == "q":
        return
    elif not messageid.isdigit():
        print 'Must enter a number for the messageid'
    else:
        mid = int(messageid)
        queryStr = "SELECT * from unprocessedmessages where id = " + messageid + ";"
        executeDBCommand(conn, cur, queryStr)
        info = cur.fetchall()
        if len(info) == 0:
            print 'Not a valid message id'
            return
        previousPhrasegroup = info[0][8]
        influencerName = info[0][2]
        phrase = info[0][1]
        otherId = getOtherId(conn, cur, influencerName)
        print '\n' + phrase
        displayTopFive(influencerName, phrase, mid, otherId)
        queryStr = "UPDATE phraseids SET numusers = numusers - 1 WHERE id = " + str(previousPhrasegroup) + ";"
        executeDBCommand(conn, cur, queryStr)

# TODO: view full conversation

def printFullConversation(conn, cur, messageinfo, manual, shouldPromptUser=True):
    print 'Displaying tail of conversation \n'
    valid_index_input = []
    queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 5;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    messageid = -1
    if info[0][7] == 'False':
        print "Skipping categorization since last message sent by us"
        return messageid
    for i in range(0, len(info)):
        index = len(info) - 1 - i
        if info[index][7] == 'True':
            messageid = info[index][0]
            print str(index) + ": " + info[index][1]
            valid_index_input.append(str(index))
        else:
            print info[index][1]
    #print messageinfo[0][1]
    phraseindex = 0 #Todo fix
    if 1 == 0:
        while phraseindex not in valid_index_input:
            if False:
                phraseindex = raw_input("Enter index of phrase to categorize: ")
            else:
                phraseindex = 0
        messageid = info[int(phraseindex)][0]
    print 'Message id : '+ str(messageid) +'\n'
    return messageid


def showSuggestion(predictedPhrasegroup, row):
    queryStr = "SELECT phrasecategories FROM phraseids where id = " + str(predictedPhrasegroup) + ";"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    print "Displaying Predicted classification below"
    print "Sentence: " + row[1]
    print "Category: " + info[0][0]
    approval = raw_input("Type 'y' to confirm, u to undo, q to quit, a to add to new category, anything else to reject: ")
    print "\n"
    if approval == 'a':
        phrasegroup = addNewCategory()
        assignToGroup(row[0], phrasegroup, 24, row[3], row[2])
        return 'a'
    if approval == 'y':
        return row[0]
    elif approval == 'q':
        return 'q'
    elif approval == 'u':
        return 'u'
    else:
        return -1

def assignToGroup(messageid, phrasegroup, uncategorizedId, userid, influencerName):    
    otherId = getOtherId(conn, cur, influencerName)
    queryStr = "SELECT phrasegroup FROM unprocessedmessages WHERE userid = (SELECT userid from unprocessedmessages WHERE id = " + str(messageid) + ");"
    executeDBCommand(conn, cur, queryStr)
    previousResponses = cur.fetchall()
    previousPhrasegroups = [previousResponses[i][0] for i in range(0, len(previousResponses))]
    if phrasegroup in previousPhrasegroups and phrasegroup != otherId and phrasegroup != uncategorizedId:
        print "That response has already been used, classifying as other"
        phrasegroupid = otherId
    queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE phrasegroup = " + str(uncategorizedId) + " AND userid = '"+ userid +"';"
    executeDBCommand(conn, cur, queryStr)
    queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(phrasegroup) + " WHERE id = " + str(messageid) + ";"
    executeDBCommand(conn, cur, queryStr)

def manualEdit(conn, cur, influencerName, messageinfo, mid):
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    otherId = getOtherId(conn, cur, influencerName)
    queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE userid = '" + messageinfo[0][3] + "' AND phrasegroup = "+ str(uncategorizedId) +";"
    executeDBCommand(conn, cur, queryStr)
    mid = printFullConversation(conn, cur, messageinfo, True)
    
    #if mid != -1:
    displayTopFive(influencerName, messageinfo[0][1], mid, otherId)

def suggestGroup(conn, cur, influencerName, messageinfo, model, vectorizer):
    mid = printFullConversation(conn, cur, messageinfo, False)
    if mid == -1:
        print "Exiting automation\n"
        return
    
    queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 3;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    
    X_test = []
    for row in info:
        X_test.append(row[1])
    clean_test_set = []

    for i in xrange(0, len(X_test)):
        clean_test_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_test[i], False)))

    # Get a bag of words for the test set, and convert to a numpy array
    test_data_features = vectorizer.transform(clean_test_set)
    test_data_features = test_data_features.toarray()

    predicted = model.predict(test_data_features)
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    phrasegroup = uncategorizedId
    editId = -1
    for i in range(0, len(info)):
        #index = len(info) - 1 - i
        if info[i][7] == 'True':
            editId = showSuggestion(predicted[i], info[i])
            if editId == 'a':
                return 'a'
            if editId == 'q':
                return 'q'
            elif editId == 'u':
                return 'u'
            elif editId != -1:
                phrasegroup = predicted[i]
                assignToGroup(editId, phrasegroup, uncategorizedId, info[i][3], influencerName)
                return -1
        else:
            break
    print "Switching to manual selection"
    manualEdit(conn, cur, influencerName, messageinfo, info[0][0])
    return 0
    #assignToGroup(info[0][0], uncategorizedId, uncategorizedId, info[0][3])

def lastMessageIsSentByUser(messageinfo):
    queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 1;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    if info[0][7] == 'True':
        return True
    else:
        return False

def checkExactMatch(conn, cur, influencerName, messageinfo):
    otherId = getOtherId(conn, cur, influencerName)
    queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + messageinfo[0][3] + "' AND influencerid = '"+ messageinfo[0][2]+"' ORDER BY timesent desc LIMIT 1;"
    executeDBCommand(conn, cur, queryStr)
    lastMessage = cur.fetchall()
    comparisonPhrase = lastMessage[0][1]
    comparisonPhrase = comparisonPhrase.replace("'", "''")
    queryStr = "SELECT phrasegroup FROM unprocessedmessages WHERE phrasegroup != 24 AND phrasegroup != -1 AND influencerid = '"+ messageinfo[0][2]+"' AND phrase = '" + comparisonPhrase +"' AND phrasegroup != " + str(otherId) + ";"
    executeDBCommand(conn, cur, queryStr)
    phrasegroups = cur.fetchall()
    if len(phrasegroups) == 0:
        print 'No exact match found in previous records'
        return -1
    phrasenums = [phrasegroups[index][0] for index in range(0, len(phrasegroups))]
    phrasenums.sort()
    phrasegroup = phrasenums[0]
    userid = messageinfo[0][3]
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    queryStr = "SELECT phrasecategories FROM phraseids where id = " + str(phrasegroup) + ";"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    if len(info) > 0:
        response = info[0][0]
        print 'Exact match found in previous records.'
        print 'Assigning: ' + lastMessage[0][1]
        print 'To: ' + response
        print 'Messageid: ' + str(lastMessage[0][0]) + '\n'
        assignToGroup(lastMessage[0][0], phrasegroup, uncategorizedId, userid, influencerName)
    return phrasegroup

def requeueMessage(conn, cur, messageid, uncategorizedId):
    queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(uncategorizedId) + " WHERE id = " + str(messageid) + ";"
    executeDBCommand(conn, cur, queryStr)

def superviseAutomation():
    print "Reviewing automated selections"
    global conn
    global cur
    influencerName = promptForInfluencerName()
    print '\n'
    if influencerName == "-1":
        return
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    otherId = getOtherId(conn, cur, influencerName)
    filename = influencerName + ".p"
    filename2 = influencerName + "train.p"
    model = pickle.load(open( filename, "rb" ) )
    clean_train_set = pickle.load(open( filename2, "rb" ) )
    vectorizer = CountVectorizer(analyzer = "word",   \
                             tokenizer = None,    \
                             preprocessor = None, \
                             stop_words = None,   \
                             max_features = 5000)
    vectorizer.fit_transform(clean_train_set)
    print 'Finished loading model'
    while True:
        queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE id = (SELECT id FROM unprocessedmessages WHERE sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent LIMIT 1) RETURNING *;"
        executeDBCommand(conn, cur, queryStr)
        messageinfo = cur.fetchall()
        if len(messageinfo) == 0:
            print 'No more uncategorized messages for this influencer \n'
            break
        if lastMessageIsSentByUser(messageinfo):
            if checkExactMatch(conn, cur, influencerName, messageinfo) == -1:
                quit = suggestGroup(conn, cur, influencerName, messageinfo, model, vectorizer)
                if quit == "q":
                    requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
                    break
                elif quit == "u":
                    requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
                    recategorizePrevious(conn, cur)
        else:
            assignToGroup(messageinfo[0][0], otherId, uncategorizedId, messageinfo[0][3], influencerName)
            print 'Last message sent by us, skipping'

# -1 indicates failure to classify manually
def groupQuestions():
    global conn
    global cur
    print '\nEnter number that corresponds to question group\n'
    influencerName = promptForInfluencerName()
    print '\n'
    if influencerName == "-1":
        return
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    otherId = getOtherId(conn, cur, influencerName)

    while True:
        queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE id = (SELECT id FROM unprocessedmessages WHERE sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent desc LIMIT 1) RETURNING *;"
        queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE id = (SELECT id FROM unprocessedmessages WHERE sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent LIMIT 1) RETURNING *;"
        executeDBCommand(conn, cur, queryStr)
        messageinfo = cur.fetchall()
        if len(messageinfo) == 0:
            print 'No more uncategorized messages for this influencer \n'
            break
        queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE userid = '" + messageinfo[0][3] + "' AND phrasegroup = "+ str(uncategorizedId) +";"
        executeDBCommand(conn, cur, queryStr)
        mid = printFullConversation(conn, cur, messageinfo, True)
        if mid != -1:
        #print '\n'
        #print 'Message ID: ' + str(messageinfo[0][0])
        #print 'Context:' + messageinfo[0][5]
        #print messageinfo[0][1] + '\n'    
        # Select and display top 5
            quit = displayTopFive(influencerName, messageinfo[0][1], mid, otherId)
        #quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
            if quit == 'q':
                requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
                break
            elif quit == 'u':
                requeueMessage(conn, cur, messageinfo[0][0], uncategorizedId)
                recategorizePrevious(conn, cur)
    

def addNewCategory():
    global conn
    global cur
    influencerName = promptForInfluencerName()
    if influencerName == "-1":
        return
    categoryType = raw_input("Enter 1 for image anything else otherwise: ")
    categoryText = raw_input("Enter new category phrase: ")
    shouldSpecifyPhrasegroup = raw_input("Enter 1 to specify phrasegroup:")
    categoryText = categoryText.replace("'", "''")
    queryStr = "INSERT INTO phraseids VALUES (DEFAULT, '" + categoryText + "', '" + influencerName + "', DEFAULT, 'N', DEFAULT, 'N') RETURNING id;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    phrasegroup = info[0][0]
    if shouldSpecifyPhrasegroup == "1":
        phrasegroup = int(raw_input("Enter phrasegrpup number: "))
    if categoryType != '1':
        responseText = raw_input("Response Text (press enter to leave empty): ")
        responseText = responseText.replace("'", "''")
        queryStr = "INSERT INTO responses VALUES (" + str(phrasegroup) + ", '" + responseText +"',DEFAULT, 'text', '" + influencerName + "');"
        executeDBCommand(conn, cur, queryStr)
    else:
        imageUrl = raw_input("Image url: ")
        imageName = raw_input("Image name: ")
        queryStr = "INSERT INTO responses VALUES (" + str(phrasegroup) + ", '" + imageName + "',DEFAULT, 'image', '" + influencerName + "', DEFAULT, DEFAULT,'" + imageUrl + "');"
        executeDBCommand(conn, cur, queryStr)
    print "Entered new category, phrasegroup:", phrasegroup
    return phrasegroup
    

def displayUnprocessedMessages():
    global conn
    global cur
    print 'Displaying all messages'
    queryStr = "SELECT * FROM unprocessedMessages WHERE sentbyuser = 'True';"    
    executeDBCommand(conn, cur, queryStr)
    dbdata = cur.fetchall()
    for row in dbdata:
        print 'Context: ' + row[5]
        print row[1] + '\n'

def textAll():
    global conn
    global cur
    queryStr = "SELECT DISTINCT userid FROM unprocessedmessages;"
    executeDBCommand(conn, cur, queryStr)
    data = cur.fetchall()
    numberlist = []
    for number in data:
        if number[0][0] == '+':
            numberlist.append(number[0])
    print 'Sending message to: ' + str(numberlist)
    test = ['+19375221858', '+15034966700']
    inputContent = raw_input("Enter phrase to send to all users: ")
    for userid in numberlist:
        data = { "content" : inputContent, "influencerId" : "electionfails", "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)

def sendImageToAll():    
    global conn
    global cur
    queryStr = "SELECT DISTINCT userid FROM unprocessedmessages;"
    executeDBCommand(conn, cur, queryStr)
    data = cur.fetchall()
    numberlist = []
    for number in data:
        if number[0][0] == '+':
            numberlist.append(number[0])
    print 'Sending message to: ' + str(numberlist)
    test = ['+19375221858', '+15034966700']
    inputContent = raw_input("Enter firebase url: ")
    mediaurl = raw_input("Enter media url: ")
    for userid in numberlist:
        data = { "content" : inputContent, "influencerId" : "electionfails", "type": "image", "userId" : userid, "mediaDownloadUrl" : mediaurl}
        url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
        headers = {'content-type': 'application/json'}
        requests.post(url, data=json.dumps(data), headers=headers)


def textOne():
    global conn
    global cur
    queryStr = "SELECT * FROM unprocessedmessages WHERE sentbyuser = 'True' AND conversationid != -2 LIMIT 1;"    
    executeDBCommand(conn, cur, queryStr)
    dbdata = cur.fetchall()
    userid = dbdata[0][3]
    print dbdata[0][1]
    print userid
    inputContent = raw_input("Enter phrase to send: ")
    data = { "content" : inputContent, "influencerId" : "morggkatherinee", "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
    headers = {'content-type': 'application/json'}
    requests.post(url, data=json.dumps(data), headers=headers)
    queryStr = "UPDATE unprocessedmessages SET conversationid = -2 WHERE id = " + str(dbdata[0][0])    
    executeDBCommand(conn, cur, queryStr)

def sendImageToOne():
    global conn
    global cur
    queryStr = "SELECT * FROM unprocessedmessages WHERE sentbyuser = 'True' AND conversationid != -2 LIMIT 1;"    
    executeDBCommand(conn, cur, queryStr)
    dbdata = cur.fetchall()
    userid = dbdata[0][3]
    print dbdata[0][1]
    print userid
    inputContent = raw_input("Enter firebase url: ")
    mediaurl = raw_input("Enter media url: ")
    data = { "content" : inputContent, "influencerId" : "electionfails", "type": "image", "userId" : userid, "mediaDownloadUrl" : mediaurl}
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
    headers = {'content-type': 'application/json'}
    requests.post(url, data=json.dumps(data), headers=headers)
    queryStr = "UPDATE unprocessedmessages SET conversationid = -2 WHERE id = " + str(dbdata[0][0])    
    executeDBCommand(conn, cur, queryStr)


def textSingleNumber():
    userid = raw_input("Input Number including +1: ")
    inputContent = raw_input("Enter phrase to send: ")
    data = { "content" : inputContent, "influencerId" : "morggkatherinee", "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
    headers = {'content-type': 'application/json'}
    requests.post(url, data=json.dumps(data), headers=headers)

def sendImageToSingleNumber():
    userid = raw_input("Input Number including +1: ")
    inputContent = raw_input("Enter firebase url: ")
    mediaurl = raw_input("Enter media url: ")
    data = { "content" : inputContent, "influencerId" : "electionfails", "type": "image", "userId" : userid, "mediaDownloadUrl" : mediaurl}
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
    headers = {'content-type': 'application/json'}
    requests.post(url, data=json.dumps(data), headers=headers)

def showCategories(conn, cur, influencerName):
    dbdata = getMatches(conn, cur, influencerName, 'NULL')
    comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]

def printContext(conn, cur, mid, influencerName):
    queryStr = "SELECT * FROM unprocessedmessages WHERE id = " + str(mid) + ";"
    executeDBCommand(conn, cur, queryStr)
    users = cur.fetchall()
    user = users[0][3]
    queryStr = "SELECT * FROM unprocessedmessages WHERE userid = '" + user + "' AND influencerid = '"+ influencerName+"' ORDER BY timesent desc LIMIT 3;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    print "PRINTING CONTEXT"
    print info[2][1]
    print info[1][1]
    print info[0][1]


def trustModel():
    influencerName = promptForInfluencerName()
    filename = influencerName + ".p"
    filename2 = influencerName + "train.p"
    model = pickle.load(open( filename, "rb" ) )
    clean_train_set = pickle.load(open( filename2, "rb" ) )
    vectorizer = CountVectorizer(analyzer = "word",   \
                             tokenizer = None,    \
                             preprocessor = None, \
                             stop_words = None,   \
                             max_features = 5000)
    vectorizer.fit_transform(clean_train_set)
    print 'Finished loading model'

    global conn
    global cur
    validCategories = [str(i) for i in range(0, 101)]
    dbdata = getMatches(conn, cur, influencerName, 'NULL')
    if len(dbdata) < 5:
        comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
    else:
        comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
    for i in range(0, len(comparisonPhrases)):
        print str(i) + ': ' + comparisonPhrases[i]
    print '\n'
    categoryText = "-1"
    while categoryText not in validCategories:
        #quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
        categoryText = raw_input("Enter category: ")
    index = int(categoryText)
    phrasegroupid = dbdata[index][0]
    
    queryStr = "SELECT * FROM unprocessedmessages WHERE sentByUser = 'True' AND phrasegroup = 24 AND influencerid = '" + influencerName + "' ORDER BY timesent;"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    
    X_test = []
    for row in info:
        X_test.append(row[1])
    clean_test_set = []

    for i in xrange(0, len(X_test)):
        clean_test_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_test[i], False)))

    # Get a bag of words for the test set, and convert to a numpy array
    test_data_features = vectorizer.transform(clean_test_set)
    test_data_features = test_data_features.toarray()
    predicted = model.predict(test_data_features)
    print predicted
    messageids = []
    messagetext = []
    for i in range(0, len(predicted)):
        if predicted[i] == phrasegroupid:
            messageids.append(info[i][0])
            messagetext.append(info[i][1])
            print info[i][1]
    print '\n'
    for i in range(0, len(messageids)):
        printContext(conn, cur, messageids[i], influencerName)
        print "\n" + str(messageids[i]) + ": " + messagetext[i]
        accept = raw_input("Type 'n' to reject, anything else to accept, q to quit: ")
        if accept == 'q':
            print 'Exiting categorizing, previous categorizations all saved'
            return
        if accept != 'n':
            queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(phrasegroupid) + " WHERE id = " + str(messageids[i]) + ";"    
            executeDBCommand(conn, cur, queryStr)
        print '\n'
    print str(len(messageids)) + " messages categorized as: " + str(phrasegroupid)

def findInCategory():
    global cur
    global conn
    queryStr = "SELECT * FROM unprocessedmessages WHERE = " + str(phrasegroupid) + " WHERE id = " + str(messageids[i]) + ";"    
    

def retrainModel():
    influencerName = promptForInfluencerName()
    categories = [i for i in range(200)]
    baseline(categories, influencerName)

def promptCategory(influencerName):
    validCategories = [str(i) for i in range(0, 101)]
    dbdata = getMatches(conn, cur, influencerName, 'NULL')
    comparisonPhrases = [dbdata[i][1] for i in range(0, len(dbdata))]
    for i in range(0, len(comparisonPhrases)):
        print str(i) + ': ' + comparisonPhrases[i]
    print '\n'
    categoryText = "-1"
    while categoryText not in validCategories:
        #quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
        categoryText = raw_input("Enter category: ")
    index = int(categoryText)
    phrasegroupid = dbdata[index][0]
    return phrasegroupid
        
def textGroup():
    global conn
    global cur
    influencerName = promptForInfluencerName()
    phrasegroupid = promptCategory(influencerName)
    queryStr = "SELECT userid FROM unprocessedmessages WHERE phrasegroup = " + str(phrasegroupid) + ";"
    executeDBCommand(conn, cur, queryStr)
    info = cur.fetchall()
    userids = []
    for row in info:
        if row[0] not in userids:
            userids.append(row[0])
    print userids
    print len(userids)
    inputContent = raw_input("Enter phrase to send: ")
    approval = raw_input("are you sure? ('y' to confirm): ")
    if approval == 'y':
        for userid in userids:
            data = { "content" : inputContent, "influencerId" : influencerName, "type": "text", "userId" : userid, "mediaDownloadUrl" : ""}
            url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToNumber'
            headers = {'content-type': 'application/json'}
            print data
            requests.post(url, data=json.dumps(data), headers=headers)


def updateResponse():
    global conn
    global cur
    influencerName = promptForInfluencerName()
    if influencerName == "-1":
        return
    dbdata = getMatches(conn, cur, influencerName, 'NULL')
    validids = []
    for row in dbdata:
        print str(row[0]) + ": " + row[1]
        validids.append(str(row[0]))
    responseid = raw_input("Input id to change: ")
    if responseid not in validids:
        print 'Not a valid id'
        return
    responseText = raw_input("Input phrase to add: ")
    responseText.replace("'", "''")
    queryStr = "UPDATE responses SET qid = -1 WHERE qid = " + responseid + ";"
    executeDBCommand(conn, cur, queryStr)
    queryStr = "INSERT INTO responses VALUES (" + responseid + ", '" + responseText + "', DEFAULT, 'text', '" + influencerName + "');" 
    executeDBCommand(conn, cur, queryStr)

def chatBot():
    
    categoryDict = {1037	 : 	"	Do you like me?	"	,
        1001	 : 	"	Hi	"	,
        1002	 : 	"	Is it really...	"	,
        1003	 : 	"	I love you	"	,
        1004	 : 	"	Compliment	"	,
        1005	 : 	"	How old are you?	"	,
        1007	 : 	"	Favorite colors	"	,
        1012	 : 	"	I'm sad	"	,
        1014	 : 	"	Are you single?	"	,
        1015	 : 	"	Deleting app	"	,
        1016	 : 	"	Who is this	"	,
        1017	 : 	"	What are you doing?	"	,
        1018	 : 	"	Can I meet you?	"	,
        1020	 : 	"	Can I ask you a question	"	,
        1023	 : 	"	Sex related/inappropriate	"	,
        1026	 : 	"	Favorite celebrities	"	,
        1027	 : 	"	OK/Yes	"	,
        1032	 : 	"	Insult	"	,
        1035	 : 	"	emoji	"	,
        1038	 : 	"	How are you?	"	,
        1039	 : 	"	Can I talk to xxx	"	,
        1040	 : 	"	Will you marry/date/love me?	"	,
        1063	 : 	"	Send me a picture/selfie	"	,
        1079	 : 	"	Intro message response	"	,
        1080	 : 	"	Answer me	"	,
        1081	 : 	"	When are you coming to my city?	"	,
        1082	 : 	"	When is your next concert?	"	,
        1083	 : 	"	I'm happy	"	,
        1084	 : 	"	I'm angry	"	,
        1085	 : 	"	I don't know	"	,
        1086	 : 	"	Goodbye	"	,
        1087	 : 	"	I will delete this app	"	,
        1088	 : 	"	Questions about selena	"	,
        1089	 : 	"	Is it too late to say sorry	"	,
        1090	 : 	"	What do you mean	"	,
        1091	 : 	"	Song Lyrics	"	,
        1092	 : 	"	JB's Birthday Date	"	,
        1093	 : 	"	I'm doing nothing	"	,
        1094	 : 	"	That's my song	"	,
        1095	 : 	"	Belieber in text	"	,
        1096	 : 	"	I miss you	"	,
        1097	 : 	"	LOL	"	,
        1037	 : 	"	How do I look?	"	,
        1099	 : 	"	How's tour	"	,
        1100	 : 	"	I went to your concert	"	,
        1101	 : 	"	Where are you	"	,
        1102	 : 	"	Good morning	"	,
        1103	 : 	"	Thanks	"	,
        1104	 : 	"	I'm not sure yet	"	,
        1105	 : 	"	Sorry	"}

    groupingDict = {
        1037	 : 	68	,
        1001	 : 	246	,
        1002	 : 	254	,
        1003	 : 	247	,
        1004	 : 	256	,
        1005	 : 	259	,
        1007	 : 	283	,
        1012	 : 	267	,
        1014	 : 	260	,
        1015	 : 	240	,
        1016	 : 	253	,
        1017	 : 	251	,
        1020	 : 	266	,
        1023	 : 	258	,
        1026	 : 	261	,
        1027	 : 	298	,
        1032	 : 	255	,
        1035	 : 	287	,
        1038	 : 	250	,
        1039	 : 	290	,
        1040	 : 	248	,
        1063	 : 	252	,
        1079	 : 	244	,
        1080	 : 	245	,
        1081	 : 	263	,
        1082	 : 	264	,
        1083	 : 	268	,
        1084	 : 	269	,
        1085	 : 	270	,
        1086	 : 	271	,
        1087	 : 	272	,
        1088	 : 	273	,
        1089	 : 	274	,
        1090	 : 	276	,
        1091	 : 	277	,
        1092	 : 	278	,
        1093	 : 	279	,
        1094	 : 	280	,
        1095	 : 	281	,
        1096	 : 	282	,
        1097	 : 	284	,
        1037	 : 	285	,
        1099	 : 	286	,
        1100	 : 	289	,
        1101	 : 	291	,
        1102	 : 	292	,
        1103	 : 	294	,
        1104	 : 	295	,
        1105	 : 	296	}

    predictedCorrectly = 0
    influencerName = promptForInfluencerName()
    categories = [i for i in range(1500)]
    thresholdDict = baseline(categories, influencerName)
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    otherId = getOtherId(conn, cur, influencerName)
    filename = influencerName + ".p"
    filename2 = influencerName + "train.p"
    model = pickle.load(open( filename, "rb" ) )
    clean_train_set = pickle.load(open( filename2, "rb" ) )
    vectorizer = CountVectorizer(analyzer = "word",   \
                                 tokenizer = None,    \
                                 preprocessor = None, \
                                 stop_words = None,   \
                                 max_features = 5000)
    vectorizer.fit_transform(clean_train_set)
    print 'Finished loading model'
    
    totalMessages = 0
    totalPredictions = 0
    queryStr = "SELECT * FROM unprocessedmessages WHERE id = (SELECT id FROM unprocessedmessages WHERE sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent);"
    queryStr = "SELECT * FROM unprocessedmessages WHERE sentbyuser = 'True' and timesent in (SELECT  max(timesent)  FROM unprocessedmessages where influencerid = '" +  influencerName + "' GROUP BY userid) order by timesent desc;"
    if influencerName == 'beliebebot':
    	queryStr =  "SELECT * FROM unprocessedmessages WHERE sentbyuser = 'True' and influencerid = 'belieberbot' and phrasegroup > 1 and phrasegroup != 243 and phrasegroup != 270;"
    elif influencerName == 'trumpbot':
    	queryStr = "select * from phraseids where phrasecategories = 'I don''t know' and influencerid = '" + influencerName + "';"
    	executeDBCommand(conn, cur, queryStr);
    	otherId = (cur.fetchall())[0][0]
    	queryStr =  "SELECT * FROM unprocessedmessages WHERE sentbyuser = 'True' and influencerid = '" + influencerName + "' and phrasegroup > 1 and phrasegroup != " + str(otherId) + ";"
    
    executeDBCommand(conn, cur, queryStr)
    data = cur.fetchall()
    
    for row in data:
        info = [row]
        if len(info) == 0:
            print 'No more uncategorized messages for ' + influencerName + '\n'
            break


        if info[0][1] != "":

            X_test = []
            for row in info:
                X_test.append(row[1])
                clean_test_set = []
                
                for i in xrange(0, len(X_test)):
                    clean_test_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_test[i], False)))

                # Get a bag of words for the test set, and convert to a numpy array
                test_data_features = vectorizer.transform(clean_test_set)
                test_data_features = test_data_features.toarray()

            predicted = model.predict(test_data_features)
            totalMessages += 1
            if predicted[0] in thresholdDict and thresholdDict[predicted[0]][0] != -1 and np.max(model.predict_proba(test_data_features)[0]) > thresholdDict[predicted[0]][0]:
                
                totalPredictions += 1

                if False:
                    print "-------------predicting\n", clean_test_set[0], "into", predicted[0], categoryDict[predicted[0]], "categoryPrediction", groupingDict[predicted[0]], "should be", row[8], "\nconfidence: ", np.max(model.predict_proba(test_data_features)[0]), "threshold:", thresholdDict[predicted[0]][0]
                    predictionExceptios = (int(groupingDict[predicted[0]]) == 261 and int(row[8]) == 262) or (int(groupingDict[predicted[0]]) == 255 and int(row[8]) == 257) or (int(groupingDict[predicted[0]]) == 255 and int(row[8]) == 265) or (int(groupingDict[predicted[0]]) == 252 and int(row[8]) == 275)
                    if int(groupingDict[predicted[0]]) == int(row[8]) or  predictionExceptios :
                        predictedCorrectly += 1
                else:
                    print "-------------predicting\n", clean_test_set[0], "into", predicted[0], "should be", row[8], "\nconfidence: ", np.max(model.predict_proba(test_data_features)[0]), "threshold:", thresholdDict[predicted[0]][0]
                    if int(predicted[0]) == int(row[8]):
                        predictedCorrectly += 1

            else:
                print "not predicting for category", predicted[0], clean_test_set, np.max(model.predict_proba(test_data_features)[0])
            if totalMessages == 300:
                print "predicted", float(totalPredictions)/totalMessages, "percent of messages"
                print "precision:", float(predictedCorrectly)/totalPredictions
                break

import time

def chatBotGrouping():
    global conn
    global cur
    print '\nEnter number that corresponds to question group\n'
    influencerName = promptForInfluencerName()
    print '\n'
    if influencerName == "-1":
        return
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    queryStr = "select * from phraseids where phrasecategories = 'I don''t know' and influencerid = '" + influencerName + "';"
    executeDBCommand(conn, cur, queryStr);
    otherId = (cur.fetchall())[0][0]

    predictedCorrectly = 0
    #influencerName = promptForInfluencerName()
    categories = [i for i in range(1500)]
    thresholdDict = baseline(categories, influencerName)
    uncategorizedId = getUncategorized(conn, cur, influencerName)
    #otherId = getOtherId(conn, cur, influencerName)
    filename = influencerName + ".p"
    filename2 = influencerName + "train.p"
    model = pickle.load(open( filename, "rb" ) )
    clean_train_set = pickle.load(open( filename2, "rb" ) )
    vectorizer = CountVectorizer(analyzer = "word",   \
                                 tokenizer = None,    \
                                 preprocessor = None, \
                                 stop_words = None,   \
                                 max_features = 5000)
    vectorizer.fit_transform(clean_train_set)
    print 'Finished loading model'

    while True:
        queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE id = (SELECT id FROM unprocessedmessages WHERE sentbyuser = 'True' AND influencerid = '" + influencerName + "' AND phrasegroup = " + str(uncategorizedId) + " ORDER BY timesent LIMIT 1) RETURNING *;"
        quit = ""
        executeDBCommand(conn, cur, queryStr)
        messageinfo = cur.fetchall()
        while len(messageinfo) == 0:
            print 'No more uncategorized messages for this influencer \n'
            time.sleep(3)
            executeDBCommand(conn, cur, queryStr)
            messageinfo = cur.fetchall()

        queryStr = "UPDATE unprocessedmessages SET phrasegroup = -1 WHERE userid = '" + messageinfo[0][3] + "' AND phrasegroup = "+ str(uncategorizedId) +";"
        executeDBCommand(conn, cur, queryStr)
        mid = printFullConversation(conn, cur, messageinfo, True, shouldPromptUser=False)
        if mid != -1:
                #print '\n'
                #print 'Message ID: ' + str(messageinfo[0][0])
                #print 'Context:' + messageinfo[0][5]
                #print messageinfo[0][1] + '\n'
                # Select and display top 5
                               #quit = raw_input("Successfully categorized. Type q to quit, u to undo a previous classification, or enter to continue: ")
            
            for row in messageinfo:
                info = [row]
                if len(info) == 0:
                    print 'No more uncategorized messages for this influencer \n'
                    break
        
        
                if info[0][1] != "":
                
                    X_test = []
                    for row in info:
                        X_test.append(row[1])
                        clean_test_set = []
                        
                        for i in xrange(0, len(X_test)):
                            clean_test_set.append(" ".join(KaggleWord2VecUtility.review_to_wordlist(X_test[i], False)))
                        
                        # Get a bag of words for the test set, and convert to a numpy array
                        test_data_features = vectorizer.transform(clean_test_set)
                        test_data_features = test_data_features.toarray()
                    
                    predicted = model.predict(test_data_features)
                    
                    print "predicted:", (predicted)


                    if predicted[0] in thresholdDict and thresholdDict[predicted[0]][0] != -1 and np.max(model.predict_proba(test_data_features)[0]) > thresholdDict[predicted[0]][0]:
                        phrasegroupid = predicted[0]
                        print "predicted",clean_test_set, phrasegroupid
                    else:
                        phrasegroupid = otherId
                        if len(clean_test_set[0]) == 0 and influencerName == 'belieberbot': #emoji
                            phrasegroupid = 287
                        print "predicred other",clean_test_set, phrasegroupid,
            

                    queryStr = "UPDATE unprocessedmessages SET phrasegroup = " + str(phrasegroupid) + " WHERE id = " + str(mid) + ";"
                    executeDBCommand(conn, cur, queryStr)
                    queryStr = "UPDATE unprocessedmessages SET autogrouped = 'True' WHERE id = " + str(mid) + ";"
                    executeDBCommand(conn, cur, queryStr)
                    queryStr = "UPDATE phraseids SET numusers = numusers + 1 WHERE id = " + str(phrasegroupid) + ";"
                    executeDBCommand(conn, cur, queryStr)
                    sendResponseToCategory(phrasegroupid)
    
    return

def sendResponseToCategory(phraseid):
    url = 'https://fierce-forest-11519.herokuapp.com/shouldSendMessageToUsers'
    headers = {'content-type': 'application/json'}
    print "sending response to: ", phraseid
    data = { "phraseId" : str(phraseid) }
    requests.post(url, data=json.dumps(data), headers=headers)

def printOptions():
    print "0: View all messages"
    print "1: Add new category"
    print "2: Group questions"
    print "3: Recategorize Previous"
    print "4: Prompt influencer"
    print "5: Send responses to Top 5"
    print "6: Send response to single question"
    print "7: Directly text all users"
    print "8: Directly text single user"
    print "9: Input number of user to text"
    print "10: Send image to all"
    print "11: Send image to single user"
    print "12: Input number of user to send image"
    print "13: Supervise automated selections"
    print "14: Retrain model"
    print "15: Trust Model"
    print "16: Update Response"
    print "17: Text Numbers for Specific Group"
    print "18: ChatBot calibration"
    print "19: ChatBot Grouping"
    

if __name__ == '__main__':

    conn = psycopg2.connect(
        database="d1jfg4556jcg85",
        user="u95kuk1lu5e68c",
        password="p9462kijpsfllp2i03nc3bqq6gt",
        host="ec2-52-204-179-136.compute-1.amazonaws.com",
        port=5432
    )
    cur = conn.cursor()

    while True:    
        printOptions()
        category = raw_input("Enter task number (Anything else to exit): ")
        if category == "0":
            displayUnprocessedMessages()    
        elif category == "1":
            addNewCategory()
        elif category == "2":
            groupQuestions()
        elif category == "3":
            recategorizePrevious(conn, cur)
        elif category == "4":
            promptInfluencer()
        elif category == "5":
            sendResponses()
        elif category == "7":
            textAll()
        elif category == "8":
            textOne()
        elif category == "9":
            textSingleNumber()
        elif category == "10":
            sendImageToAll()
        elif category == "11":
            sendImageToOne()
        elif category == "12":
            sendImageToSingleNumber()
        elif category == "13":
            superviseAutomation()
        elif category == "14":
            retrainModel()
        elif category == "15":
            trustModel()
        elif category == "16":
            updateResponse()
        elif category == "17":
            textGroup()
        elif category == "18":
            chatBot()
        elif category == "19":
            chatBotGrouping()
        else:
            break

    conn.close()




