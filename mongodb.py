import pymongo, os, datetime, pytz

client = pymongo.MongoClient(os.environ['mongodb_uri'])
db = client[os.environ['mongodb_db']]

##
## URL REDIRECT KEYS ##
##
keys = db.keys

def insert(usr:str, url:str, key:str):
	# return True if insert successful, else False
	content = {
		"user": usr,
		"url": url,
		"key": key,
		"date": datetime.datetime.now(datetime.timezone.utc).astimezone(pytz.timezone('Asia/Manila'))
	}
	return True if keys.insert_one(content).inserted_id is not None else False

def query(key:str):
	# return dict if exists, else None
	content = keys.find_one({"key": key})
	return content if content else None

##
## USERS ##
##
usrs = db.users

def regUser(usr:str, pswd:str):
	# return True if insert successful, else False
	content = {
		"user": usr,
		"password": pswd,
		"date": datetime.datetime.now(datetime.timezone.utc).astimezone(pytz.timezone('Asia/Manila'))
	}
	return True if usrs.insert_one(content).inserted_id is not None else False

def checkUser(usr:str):
	# return dict
	content = usrs.find_one({"user": usr})
	return content

##
## DEOBFUSCATION KEYS ##
##
symkey = db.symkey

def saveKey(urlKey:str, cipherKey:str, nonce:str):
	content = {
		"key": urlKey,
		"symkey": cipherKey,
		"nonce": nonce
	}
	return True if symkey.insert_one(content).inserted_id is not None else False

def getKey(urlKey:str):
	content = symkey.find_one({"key": urlKey})
	return content