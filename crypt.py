from Crypto.Cipher import ChaCha20 as cc
from base64 import b64encode as b64e, b64decode as b64d
import string, random, hashlib as h

# url safe random string generator
def r( size:int = 512, charset:str = string.ascii_lowercase + string.digits + string.ascii_uppercase + '-_+' ):
	return ''.join( random.SystemRandom().choice( charset ) for _ in range( size ) )

def enc(content:str, symkey:str=r(32)):
	cipher = cc.new(key=symkey.encode('utf-8'))
	ciphertext = cipher.encrypt(content.encode('utf-8'))
	nonce = b64e(cipher.nonce).decode('utf-8')
	ct = b64e(ciphertext).decode('utf-8')
	return {'nonce': nonce, 'content': ct, 'symkey': symkey}

def dec(content:str, nonce:str, symkey:str):
	cipher = cc.new(key=symkey.encode('utf-8'), nonce=b64d(nonce))
	result = cipher.decrypt(b64d(content)).decode('utf-8')
	return result

def crh(content:str, salt:str):
	return h.sha512(content.encode() + salt.encode()).hexdigest()