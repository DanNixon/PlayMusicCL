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

# `devices` is a list of dictionaries like this:
# {u'carrier': u'Google',
#  u'deviceType': 2,
#  u'id': u'0x1111111111111111',
#  u'lastAccessedFormatted': u'January 1, 1999',
#  u'lastAccessedTimeMillis': 915148800,
#  u'lastEventTimeMillis': 915148800,
#  u'manufacturer': u'LGE',
#  u'model': u'Nexus 5',
#  u'name': u''}]
for device in devices:
	if device['deviceType'] == 2:
		print "Device:{d[manufacturer]} {d[model]}\tid:{d[id]}".format(d=device)
