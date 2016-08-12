import os
import psycopg2
import urlparse
import time


def addUser(userID, name, most_recent_message):	
	conn = psycopg2.connect(
    	database="dauueuhdllo0n5",
    	user="xvhkotqwxjqqvc",
    	password="raSBIobNzUn8YQ6njvErtp9Llx",
    	host="ec2-54-235-85-65.compute-1.amazonaws.com",
    	port=5432
	)
	cur = conn.cursor()
	timestamp = int(time.time())
	cur.execute("INSERT INTO messagedata2 (userID, name, message) VALUES (%s, %s, %s)", (userID, name, most_recent_message))
	conn.commit()
	conn.close()
	#cur.execute("SELECT data FROM users2 WHERE userid=1")
	#messages = cur.fetchone()
	#messages[0].append("Message 3")
	#print messages[0]
#urlparse.uses_netloc.append("postgres")
#url = urlparse.urlparse(os.environ["postgres://nhxgszujweytgn:NyBIa693v4cKcjtqZg9rYurJBg@ec2-54-235-85-65.compute-1.amazonaws.com:5432/d5uvgsv9j78l1t"])


#cur.execute("CREATE TABLE test3 (id serial PRIMARY KEY, num integer, data varchar);")
#cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))
#cur.execute("CREATE TABLE messagedata2 (pin serial PRIMARY KEY, userID integer, name varchar, message varchar, time TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
#cur.execute("INSERT INTO users (userID, name, pageID, data) VALUES (%s, %s, %s, %s)", (1,"joe", 100, "abc'def"))
#mylist = ["message 1", "message 2"]
addUser(1, "sam","datawoooo")


