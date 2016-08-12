from requests import get

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

val1 = sss('a small violin is being played by a girl', 'a child is performing on a tiny instrument', sss_url, type='concept')
print val1


val3 = sts('a small violin is being played by a girl', 'a child is performing on a tiny instrument', sts_url)
print val3
