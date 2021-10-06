from Crypto.Cipher import ChaCha20 as cc
from base64 import b64encode as b64
import string, random

# url safe random string generator
def r( size:int = 512, charset:str = string.ascii_lowercase + string.digits + string.ascii_uppercase + '-_+' ):
	return ''.join( random.SystemRandom().choice( charset ) for _ in range( size ) )

def enc(content:str, key:str):
	cipher = cc.new(key=key)
	ciphertext = cipher.encrypt(content)
	nonce = b64(cipher.nonce).decode('utf-8')
	ct = b64(ciphertext).decode('utf-8')
	return {'nonce': nonce, 'content': ct}

def denc(content:str, nonce:str, key:str):
	cipher = cc.new(key=key, nonce=nonce)
	result = cipher.decrypt(content)
	return result