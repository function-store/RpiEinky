# WebclientDAT callbacks for RpiEinky Upload Service
# This file provides minimal bridge callbacks that forward events to the extension

def getExtension():
	"""Get the extension instance"""
	try:
		return ext.RpiEinkyUploadExt
	except:
		return None

def onConnect(webClientDAT, id):
	"""Called when WebclientDAT connection is established"""
	ext = getExtension()
	if ext:
		ext.onWebClientConnect(webClientDAT, id)
	return
	
def onDisconnect(webClientDAT, id):
	"""Called when WebclientDAT connection is closed"""
	ext = getExtension()
	if ext:
		ext.onWebClientDisconnect(webClientDAT, id)
	return

def onResponse(webClientDAT, statusCode, headerDict, data, id):
	"""Called when response is received from server"""
	ext = getExtension()
	if ext:
		ext.onWebClientResponse(webClientDAT, statusCode, headerDict, data, id)
	return
	