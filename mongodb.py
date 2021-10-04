import pymongo, os, datetime, pytz

client = pymongo.MongoClient(os.environ['mongodb_uri'])
db = client[os.environ['mongodb_db']]
coll = db['keys']
posts = db.posts

def insert(url:str, key:str):
	# return True if insert successful, else False
	content = {
		"url": url,
		"key": key,
		"date": datetime.datetime.now(datetime.timezone.utc).astimezone(pytz.timezone('Asia/Manila'))
	}
	return True if posts.insert_one(content).inserted_id is not None else False

def query(key:str):
	# return dict if exists, else None
	content = posts.find_one({"key": key})
	return content