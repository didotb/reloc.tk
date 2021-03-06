from flask import Flask, redirect, request, abort, render_template, url_for, send_from_directory
from flask_simplelogin import SimpleLogin, login_required, is_logged_in
from flask_wtf import FlaskForm as FF
from flask_bootstrap import Bootstrap
from flask_compress import Compress
from flask_qrcode import QRcode
from wtforms import StringField, SubmitField, TextAreaField, PasswordField
from wtforms.validators import URL, Optional, Length, InputRequired, Email, EqualTo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mongodb import insert, query, checkUser, saveKey, getKey, regUser, listAll
from crypt import r, crh, enc, dec
from urllib.parse import quote
import os, signal, smtplib, ssl, gnupg, datetime, pytz

# initiate flask app
app = Flask("reloc-tk")

# initiate QRcode
QRcode(app)

# initiate gnupg active directory
gpg = gnupg.GPG(gnupghome=os.environ['gnupg_home-dir'])
gpg.encoding = 'utf-8'

# redirect key checker
def check_key( ckey:str ):
	result = query(key=ckey)
	deob = getKey(ckey) if result is not None else None
	return dec(result['url'], deob['nonce'], deob['symkey']) if result is not None else False

# insert key to database
def send_key( key:str, url:str, usr:str ):
	result = insert(usr, url, key)
	return key if result is True else None

# redirect form
class redir_url(FF):
	full_url = StringField( "Full URL (include http(s)) *: ", validators = [ URL(), InputRequired( message = "\'Full URL\' field is important." ) ] )
	custom_key = StringField( "Custom key (optional): ", validators = [ Optional(), Length( min=6, max=20 ) ] )
	submit = SubmitField( "Submit" )

# contact form
class contact_me(FF):
	reply_email = StringField( "Your Email:", validators=[Email(granular_message=True), InputRequired(message="\'Email\' field is required.")] )
	pgp = StringField( "Public Key URL:", validators=[URL(message="Invalid URL."), Optional()] )
	message = TextAreaField( "Message:", validators=[InputRequired(message="\'Message\' field is required.")] )
	submit = SubmitField( "Submit" )

# register form
class reg(FF):
	username = StringField("Username:", validators=[InputRequired()])
	password = PasswordField("Password:", validators=[InputRequired(), EqualTo("confirm")])
	confirm = PasswordField("Confirm Password:", validators=[InputRequired()])
	submit = SubmitField("Submit")

# login form
class login(FF):
	username = StringField("Username", validators=[InputRequired()])
	password = PasswordField("Password", validators=[InputRequired()])
	submit = SubmitField("Submit")

	'''def validate_username(form, field):
		user = field.data.lower()
		db_data = checkUser(user)
		if (db_data is None):
			raise ValidationError("Invalid credentials")'''

# credential checker
def check_user( user ):
	global gUser
	gUser = user.get('username').lower()
	userData = checkUser(gUser)
	if userData is None:
		return False
	pswd = quote(user.get('password'), safe='')
	try:
		hash = checkUser(gUser)['password']
	except TypeError:
		return False
	return True if crh(pswd, gUser) == hash else False

# local environment configurations
app.config['SECRET_KEY'] = r(4096)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
app.config['KILL_SIGNAL'] = r(50)
app.config['SIMPLELOGIN_HOME_URL'] = '/urls/'
app.config['SIMPLELOGIN_LOGIN_URL'] = '/login/'
app.config['SIMPLELOGIN_LOGOUT_URL'] = '/logout/'
app.config['BOOTSTRAP_CDN_FORCE_SSL'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['COMPRESS_ALGORITHM'] = 'br'
app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'application/javascript', 'image/vnd.microsoft.icon']
app.config['COMPRESS_BR_LEVEL'] = 11
app.config['COMPRESS_BR_MODE'] = 1

##
## MAIN REDIRECTOR ##
##
@app.route( '/<key>/' )
def redr( key ):
	dt = datetime.datetime.now( datetime.timezone.utc ).astimezone( pytz.timezone( 'Asia/Manila' ) ).strftime( '(%b %d, %Y - %X)\n' )
	header = 'full header request: ' + str( request.headers )
	with open( 'access.log', 'a' ) as file:
		file.write( f'{dt}{header}' )
	result = check_key( key )
	return redirect( location = result ) if result else abort( 404, description = 'Redirect does not exist.' )

##
## Init modules the main redir doesn't need ##
##
# SimpleLogin
SimpleLogin( app=app, login_checker=check_user, login_form=login )
# flask compression
Compress().init_app(app)
# bootstrap
Bootstrap( app )

##
## FLASK ROUTES ##
##
# homepage
@app.route( '/' )
def home():
	dt = datetime.datetime.now( datetime.timezone.utc ).astimezone( pytz.timezone( 'Asia/Manila' ) ).strftime( '(%b %d, %Y - %X)\n' )
	header = 'full header request: ' + str( request.headers )
	with open( 'access.log', 'a' ) as file:
		file.write( f'{dt}{header}' )
	signl = request.args.get('signal')
	if signl == app.config['KILL_SIGNAL']:
		# stop the app
		os.kill( os.getpid(), signal.SIGTERM )
		return 'error stopping app'
	else:
		return render_template( 'home.html' )

# redirect url maker homepage
@app.route( app.config['SIMPLELOGIN_HOME_URL'], methods=['GET','POST'] )
@login_required
def urls():
	if is_logged_in():
		form = redir_url()
		msg = ""
		errtype = ""
		formmsg = ""
		url_tmpl = ""
		if form.validate_on_submit():
			rand_key = form.custom_key.data if len( form.custom_key.data ) > 1 else r(6)
			full_url = form.full_url.data
			if check_key( rand_key ) is False:
				encUrl = enc(content=full_url)
				if saveKey(rand_key,encUrl['symkey'],encUrl['nonce']):
					result = send_key( key = rand_key, url = encUrl['content'], usr = gUser )
					if result is not None:
						msg = "Record added. "
						errtype = "success"
						url_tmpl = "https://reloc.tk/"+result+"/"
					else:
						msg = "Error adding record"
						errtype = "error"
				else:
					msg = "Error obfuscating URL: Please contact Andrew."
					errtype = "error"
			elif check_key( rand_key ):
				msg = "Key " + rand_key + " exists. Try again"
				errtype = "error"
			form.full_url.data = ''
			form.custom_key.data = ''
		else:
			formmsg = form.full_url.errors + form.custom_key.errors
		return render_template( 'urls.html', msg=msg, url=url_tmpl, form=form, user=gUser, formmsg=formmsg, err=errtype, stop=app.config['KILL_SIGNAL'] )
	return redirect( location = app.config['SIMPLELOGIN_LOGIN_URL'] )

# user get links
@app.route('/links/')
@login_required
def edit_links():
	list = listAll(gUser)
	return render_template('links.html', user=gUser, list=list)

# user register
@app.route( '/register/', methods=['POST', 'GET'] )
def register():
	form = reg()
	if request.method == 'POST':
		usr = quote(form.username.data.lower(), safe='')
		pswd = quote(form.password.data, safe='')
		cnfrm = quote(form.confirm.data, safe='')
		if checkUser(usr) is not None:
			return render_template("register.html", form=form, msg="User already exists.", err="error")
		if pswd == cnfrm:
			hash = crh(pswd,usr)
			if regUser(usr,hash):
				return redirect(location=app.config['SIMPLELOGIN_HOME_URL'])
	return render_template("register.html", form=form)

# personal pgp public key
@app.route( '/pgp/' )
def my_pgp():
	with open('pgp.txt', 'r') as f:
		pgp = f.read()
		f.close()
	return render_template("pgp.html", pgp=pgp)

# contact me form
@app.route( '/contact/', methods=['POST', 'GET'] )
def contact():
	form = contact_me()
	if request.method == 'POST':
		reply_to = form.reply_email.data
		recv = os.environ['ddotbtk_email']
		subject = f"Reloc Contact {reply_to}"
		port = 465
		ssl_ctx = ssl.create_default_context()
		gpg_message = gpg.encrypt(data=form.message.data, recipients=['BA4D90AB5735644A'], sign=True, passphrase=os.environ['gnupg_passwd'], armor=True)
		body = f"PGP Link: {form.pgp.data}\n\n{gpg_message}"

		message = MIMEMultipart()
		message["From"] = recv
		message["To"] = recv
		message["Reply-To"] = reply_to
		message["Subject"] = subject
		message.attach( MIMEText(body, "plain") )

		with smtplib.SMTP_SSL("smtp.gmail.com", port, context=ssl_ctx) as svr:
			svr.login(os.environ['gmail-user'], os.environ['gmail-passwd'])
			svr.sendmail(recv, recv, message.as_string())

		return redirect(url_for('contact'))
	return render_template('contact.html', form=form)

# favicon
@app.route('/favicon.ico')
def favicon():
	#return render_template('favicon.ico')
	return send_from_directory(os.path.join(app.root_path, 'templates'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

def clear_log():
	with open('access.log', 'w') as log:
		print('Clearing logs...')
		log.close()
	print('Logs cleared.')

# run app
if __name__ == "__main__":
	clear_log()
	app.run( host = '0.0.0.0', port = 80 )