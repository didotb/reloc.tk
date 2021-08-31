from playhouse.sqlcipher_ext import SqlCipherDatabase, Model, AutoField, CharField, TextField, DateTimeField
import datetime, pytz, os

db = SqlCipherDatabase(None)

class db_keys(Model):
	id = AutoField( primary_key = True, null = False )
	key = CharField( null = False, unique = True, max_length = 20 )
	url = TextField( null = False )
	added = DateTimeField(  null = False, default = datetime.datetime.now( datetime.timezone.utc ).astimezone( pytz.timezone('Asia/Manila') ) )

	class Meta:
		database = db

db.init( 'db.db', passphrase = os.environ['bUMaJisl'] )

if not os.path.exists( 'db.db' ):
	db.connect()
	db.create_tables( [db_keys] )

db.close()