from flask import Flask, redirect, request, abort, render_template, url_for
from flask_simplelogin import SimpleLogin as sl, login_required, is_logged_in
from flask_wtf import FlaskForm as FF
from flask_bootstrap import Bootstrap
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import URL, Optional, Length, InputRequired, Email
from flask_compress import Compress
from db_control import db_keys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import string, random, os, hashlib as h, signal, smtplib, ssl, gnupg

# initiate flask app
app = Flask( __name__ )

# initiate gnupg active directory
gpg = gnupg.GPG(gnupghome=os.environ['gnupg_home-dir'])
gpg.encoding = 'utf-8'

# random string generator
def r( size:int = 512, charset:str = string.ascii_lowercase + string.digits + string.ascii_uppercase + '-_+' ):
	return ''.join( random.SystemRandom().choice( charset ) for _ in range( size ) )

# user checker for SimpleLogin
def check_user( user ):
	return True if ( h.sha512( os.environ['s1'].encode() + user.get('username').encode() + os.environ['s2'].encode() ).hexdigest() == os.environ['flask_user'] ) and ( h.sha512( os.environ['sp1'].encode() + os.environ['sp2'].encode() + user.get('password').encode() + os.environ['sp2'].encode() ).hexdigest() == os.environ['flask_passwd'] ) else False

# redirect key checker
def check_key( ckey:str, print:bool = False ):
	query = db_keys.get_or_none( db_keys.key == ckey )
	if print is False:
		return True if query is None else False
	else:
		return query.url if query is not None else None

# insert key to database
def send_key( key:str, url:str ):
	insert = db_keys( key = key, url = url )
	result = insert.save()
	return key if result >= 1 else None

# form content
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

# local environment configurations
app.config[ 'SECRET_KEY' ] = r(4096)
app.config[ 'SESSION_COOKIE_SECURE' ] = True
app.config[ 'SESSION_COOKIE_SAMESITE' ] = 'Strict'
app.config[ 'KILL_SIGNAL' ] = r(50)
app.config[ 'SIMPLELOGIN_HOME_URL' ] = '/urls/'
app.config[ 'SIMPLELOGIN_LOGIN_URL' ] = '/login/'
app.config[ 'SIMPLELOGIN_LOGOUT_URL' ] = '/logout/'
app.config[ 'BOOTSTRAP_CDN_FORCE_SSL' ] = True
app.config[ 'TEMPLATES_AUTO_RELOAD' ] = True
app.config[ 'COMPRESS_ALGORITHM' ] = 'br'
app.config[ 'COMPRESS_MIMETYPES' ] = ['text/html', 'text/css', 'application/javascript']
app.config[ 'COMPRESS_BR_LEVEL' ] = 11
app.config[ 'COMPRESS_BR_MODE' ] = 1

##
## MAIN REDIRECTOR ##
##
@app.route( '/<url>/' )
def redr( url ):
	return redirect( location = check_key( url, True ), code = 301 ) if check_key( url ) is False else abort( 404, description = 'Redirect does not exist.' )

##
## Initialize modules after main redirector ##
##
# SimpleLogin
sl( app = app, login_checker = check_user )
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
	signl = request.args.get('signal')
	if signl == app.config['KILL_SIGNAL']:
		# stop the app
		os.kill( os.getpid(), signal.SIGTERM )
		return 'error stopping app'
	else:
		return render_template( 'home.html' )

# redirect url maker homepage
@app.route( app.config[ 'SIMPLELOGIN_HOME_URL' ], methods=['GET','POST'] )
@login_required( username = 'didotb' )
def urls():
	if is_logged_in( username = 'didotb' ):
		form = redir_url()
		msg = ""
		errtype = ""
		formmsg = ""
		url_tmpl = ""
		if form.validate_on_submit():
			full_url = form.full_url.data
			rand_key = form.custom_key.data if len( form.custom_key.data ) > 1 else r(6)
			if check_key( ckey = rand_key ):
				result = send_key( key = rand_key, url = full_url )
				if result is not None:
					msg = "Record added. "
					errtype = "success"
					url_tmpl = "reloc.tk/"+result+"/"
				else:
					msg = "Error adding record"
					errtype = "error"
			elif check_key( ckey = rand_key ) is False:
				msg = "Key " + rand_key + " exists. Try again"
				errtype = "error"
		else:
			formmsg = form.full_url.errors + form.custom_key.errors
		return render_template( 'urls.html', msg=msg, url=url_tmpl, form=form, formmsg=formmsg, err=errtype, stop=app.config['KILL_SIGNAL'] )
	return redirect( location = app.config[ 'SIMPLELOGIN_LOGIN_URL' ] )

@app.route( '/pgp/' )
def my_pgp():
	with open('pgp.txt', 'r') as f:
		pgp = f.read()
	return render_template("pgp.html", pgp=pgp)

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

if __name__ == "__main__":
	app.run( host = '0.0.0.0', port = 80 )