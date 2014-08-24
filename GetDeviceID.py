#!/usr/bin/python

# Google Play Music device ID grabber
# Used to get a device ID from the Google Music API to use with the Mobileclient
# dan-nixon.com
# Date: 04/03/2014


import gmusicapi
from getpass import getpass


print "Username: ",
user = raw_input()
passwd = getpass()

api = gmusicapi.Webclient()
api.login(user, passwd)
devices = api.get_registered_devices()

for device in devices:
	if device['type'] == 'PHONE':
		print "Name:{d[name]}\tid:{d[id]}".format(d=device)
