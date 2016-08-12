import os
import sqlite3
import csv

conn = sqlite3.connect('../database.sqlite')
curs = conn.cursor()

subreddits = ["AskReddit", "videos", "funny", "pics", "gifs", "WTF", "nfl" , "nba", 
	"aww", "technology", "movies", "Fallout", "Bitcoin", "gaming", "politics", "Music",
	"todayilearned", "worldnews", "news", "relationships", "soccer", "StarWars", "trees", 
	"atheism", "science", "IAmA", "askscience", "explainlikeimfive", "books", "Showerthoughts",
	"space", "Fitness", "Jokes", "food"]

with open('data/example.csv','w') as out:
	csv_out=csv.writer(out)
	for s in subreddits:
		data = curs.execute('select * from May2015 where subreddit="'+s+'" limit 20;')
		for row in data:
			csv_out.writerow([unicode(s).encode("utf-8") for s in row])