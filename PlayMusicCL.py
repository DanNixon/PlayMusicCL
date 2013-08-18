#!/usr/bin/python
# -*- coding: utf_8 -*-

## Command line client for Google Play Music
## Copyright: Dan Nixon 2012-13
## dan-nixon.com
## Version: 0.3.5
## Date: 18/08/2013

import thread, time, shlex, random, sys
from gmusicapi import Webclient
from operator import itemgetter
from getpass import getpass
import gobject, glib, pygst
import gst

m_client = None
m_player = None
last_fm = None
clh = None
run = True

class switch(object):
	def __init__(self, value):
		self.value = value
		self.fall = False

	def __iter__(self):
		yield self.match
		raise StopIteration
    
	def match(self, *args):
		if self.fall or not args:
			return True
		elif self.value in args:
			self.fall = True
			return True
		else:
			return False

class gMusicClient(object):
	logged_in = False
	api = None
	playlists = dict()
	library = dict()
	
	def __init__(self, email, password):
		self.api = Webclient()
		logged_in = False
		attempts = 0
		if len(password) is 0:
			password = getpass("Google password:")
		while not self.logged_in and attempts < 3:
			self.logged_in = self.api.login(email, password)
			attempts += 1

	def __del__(self):
		self.api.logout()

	def updateLocalLib(self):
		songs = list()
		self.library = dict()
		self.playlists = dict()
		songs = self.api.get_all_songs()
		for song in songs:
			song_title = song["title"]
			if song["artist"] == "":
				song_artist = "Unknown Artist"
			else:
				song_artist = song["artist"]
			if song["album"] == "":
				song_album = "Unknown Album"
			else:
				song_album = song["album"]
			if not (song_artist in self.library):
				albums_dict = dict()
				self.library[song_artist] = albums_dict
			if not (song_album in self.library[song_artist]):
				song_list = list()
				self.library[song_artist][song_album] = song_list
			self.library[song_artist][song_album].append(song)
		plists = self.api.get_all_playlist_ids(auto=True, user=True)
		for u_playlist, u_playlist_id in plists["user"].iteritems():
			self.playlists[u_playlist] = self.api.get_playlist_songs(u_playlist_id[0])
		self.playlists["Thumbs Up"] = [song for song in songs if song['rating'] == 5]

	def getSongStream(self, song):
		url = self.api.get_stream_urls(song["id"])[0]
		return url
	
	def thumbsUp(self, song):
		try:
			song["rating"] = 5
			song_list = [song]
			self.api.change_song_metadata(song_list)
			print "Gave a Thumbs Up to {0} by {1} on Google Play.".format(song["title"].encode("utf-8"), song["artist"].encode("utf-8"))
		except:
			print "Error giving a Thumbs Up on Google Play."

class mediaPlayer(object):
	player = None
	now_playing_song = None
	queue = list()
	queue_index = -1
	play_mode = 0
	
	def __init__(self):
		thread.start_new_thread(self.playerThread, ())
	
	def __del__(self):
		self.now_playing_song = None
		self.player.set_state(gst.STATE_NULL)
	
	def print_current_song(self):
		song = self.now_playing_song
		if not song is None:
			track = m_player.now_playing_song["title"]
			artist = m_player.now_playing_song["artist"]
			print "Now playing {0} by {1}".format(track.encode("utf-8"), artist.encode("utf-8"))
		else:
			print "No song playing."

	def set_terminal_title(self):
		if self.now_playing_song == None or self.player.get_state()[1] == gst.STATE_PAUSED:
			sys.stdout.write("\x1b]2;Google Play Music\x07")
			return
		title_string = "\x1b]2;{0} - {1}\x07".format(self.now_playing_song["title"].encode("utf-8"), self.now_playing_song["artist"].encode("utf-8"))
		thread.start_new_thread(cl_print, (title_string, 1))
	
	def playerThread(self):
		if self.player == None:
			self.player = gst.element_factory_make("playbin2", "player")
			self.player.set_state(gst.STATE_NULL)
			bus = self.player.get_bus()
			bus.add_signal_watch()
			bus.connect("message", self.songEndHandle)
			glib.MainLoop().run()
	
	def playSong(self, song):
		global m_client
		global lcd_man
		global last_fm
		song_url = m_client.getSongStream(song)
		try:
			self.player.set_property("uri", song_url)
			self.player.set_state(gst.STATE_PLAYING)
			self.now_playing_song = song
			self.print_current_song()
			self.set_terminal_title()
			last_fm.updateNowPlaying(song)
		except AttributeError:
			print "Player error!"

	def togglePlayback(self):
		try:
			player_state = self.player.get_state()[1]
			if player_state == gst.STATE_PAUSED:
				self.player.set_state(gst.STATE_PLAYING)
				self.set_terminal_title()
				print "Resumng playback."
			elif player_state == gst.STATE_PLAYING:
				self.player.set_state(gst.STATE_PAUSED)
				self.set_terminal_title()
				print "Pauseing playback."
				print ""
			elif player_state == gst.STATE_NULL:
				self.playNextInQueue(1)
		except AttributeError:
			print "Player error!"

	def stopPlayback(self):
		try:
			self.player.set_state(gst.STATE_NULL)
			self.now_playing_song = None
		except AttributeError:
			print "Player error!"

	def songEndHandle(self, bus, message):
		if message.type == gst.MESSAGE_EOS:
			self.nextSong(1)

	def playNextInQueue(self, n):
		if (self.play_mode % 2) == 0:
			self.queue_index += n
		else:
			self.queue_index = random.randint(0, (len(self.queue) - 1))
		if (self.queue_index < len(self.queue)) and (self.queue_index >= 0):
			next_song = self.queue[self.queue_index]
			self.playSong(next_song)
		else:
			if (self.play_mode == 2) or (self.play_mode == 3):
				self.queue_index = -1
				self.playNextInQueue(1)
			else:
				self.stopPlayback()
				self.set_terminal_title()

	def addToQueue(self, song):
		self.queue.append(song)

	def nextSong(self, n):
		global last_fm
		last_fm.scrobbleSong(self.now_playing_song)
		self.stopPlayback()
		self.playNextInQueue(n)

class lastfmScrobbler(object):
	API_KEY = "a0790cb91b8799b0eda1f60d3924b676"
	API_SECRET = "5007f138c5fef4278f36c70d760f24b7"
	session = None
	enabled = False
	
	def __init__(self, username, password, use):
		if use:
			if len(password) is 0:
				password = getpass("Last.fm password:")
			import pylast
			password_hash = pylast.md5(password)
			self.session = pylast.LastFMNetwork(api_key = self.API_KEY, api_secret = self.API_SECRET, username = username, password_hash = password_hash)
		self.enabled = use
	
	def loveSong(self, song):
		if not song == None and self.enabled:
			print "Loving {0} by {1} on Last.fm.".format(song["title"].encode("utf-8"), song["artist"].encode("utf-8"))
			thread.start_new_thread(self.workerFunction, (1, song))
		else:
			print "No song playing or Last.fm disabled."
	
	def updateNowPlaying(self, song):
		if not song == None and self.enabled:
			thread.start_new_thread(self.workerFunction, (2, song))
		
	def scrobbleSong(self, song):
		if not song == None and self.enabled:
			thread.start_new_thread(self.workerFunction, (3, song))
	
	def workerFunction(self, function, song):
		title = song['title']
		artist = song['artist']
		if artist == "":
			artist = "Unknown Artist"
		for case in switch(function):
			if case(1):
				track = self.session.get_track(artist, title)
				track.love()
				break
			if case(2):
				self.session.update_now_playing(artist, title)
				break
			if case(3):
				self.session.scrobble(artist, title, int(time.time()))
				break

class commandLineHandler(object):
	CON_PLISTS = 1
	CON_PLTRACKS = 2
	CON_ARTISTS = 3
	CON_ALBUMS = 4
	CON_TRACKS = 5
	
	QF_LIST = 1
	QF_ADDPLI = 2
	QF_ADDART = 3
	QF_ADDALB = 4
	QF_ADDTRA = 5
	
	SINGLE_PG_LEN = 20
	
	def __del__(self):
		title_string = "\x1b]2;I played music once, but then I took a SIGTERM to the thread.\x07"
		sys.stdout.write(title_string)
	
	def parseCL(self, in_string):
		if len(in_string) is 0:
			global m_player
			m_player.print_current_song()
			print ""
			return
		function = None
		f_args = None
		try:
			args = shlex.split(in_string)
			function = args[0].upper()
		except IndexError:
			pass
		for case in switch(function):
			if case("LIST"):
				self.listHandler(args)
				print ""
				break
			if case("QUEUE"):
				self.queueHandler(args)
				print ""
				break
			if case("PAUSE"):
				global m_player
				m_player.togglePlayback()
				break
			if case("PLAY"):
				global m_player
				m_player.togglePlayback()
				break
			if case("LIKE"):
				global last_fm
				global m_client
				global m_player
				last_fm.loveSong(m_player.now_playing_song)
				m_client.thumbsUp(m_player.now_playing_song)
				print ""
				break
			if case("LOVE"):
				self.parseCL("LIKE")
				return
				break
			if case("PMODE"):
				self.pmHandler(args)
				print ""
				break
			if case("NEXT"):
				global m_player
				try:
					n = int(args[1])
				except ValueError:
					n = 1
				except IndexError:
					n = 1
				m_player.nextSong(n)
				break
			if case("NOW"):
				global m_player
				m_player.print_current_song()
				print ""
				break
			if case("EXIT"):
				global run
				print "じゃね"
				run = False
				break
			if case():
				print "Argument error!"
				print ""

	def queueHandler(self, args):
		global m_player
		global m_client
		function = 0
		page_no = 0
		for case in switch(len(args)):
			if case(1):
				function = self.QF_LIST
				page_no = 1
				break
			if case(2):
				try:
					page_no = int(args[1])
					function = self.QF_LIST
				except ValueError:
					function = self.QF_ADDART
				break
			if case(3):
				if args[1].upper() == "PLIST":
					function = self.QF_ADDPLI
				else:
					function = self.QF_ADDALB
				break
			if case(4):
				function = self.QF_ADDTRA
				break
		global m_client
		global m_player
		for case in switch(function):
			if case(self.QF_LIST):
				queue = m_player.queue
				print "Tracks in queue (page {0}/{1})".format(page_no, ((len(queue) / self.SINGLE_PG_LEN) + 1))
				lower_bound = (page_no - 1) * self.SINGLE_PG_LEN
				upper_bound = page_no * self.SINGLE_PG_LEN
				for i in range(lower_bound, upper_bound):
					try:
						print "{0} - {1}".format(queue[i]["artist"].encode("utf-8"), queue[i]["title"].encode("utf-8"))
					except IndexError:
						pass
				break
			if case(self.QF_ADDPLI):
				try:
					playlist = m_client.playlists[args[2]]
					for song in playlist:
						m_player.addToQueue(song)
					print "Added {0} tracks from {1} to queue".format(len(playlist), args[2])
				except KeyError:
					print "Cannot find playlist."
				break
			if case(self.QF_ADDART):
				try:
					artist = m_client.library[args[1]]
					count = 0
					for album in artist:
						for song in artist[album]:
							m_player.addToQueue(song)
							count += 1
					print "Added {0} tracks by {1} to queue".format(count, args[1])
				except KeyError:
					print "Cannot find artist."
				break
			if case(self.QF_ADDALB):
				try:
					album = m_client.library[args[1]][args[2]]
					count = 0
					for song in album:
						m_player.addToQueue(song)
						count += 1
					print "Added {0} tracks from {1} by {2} to queue".format(count, args[2], args[1])
				except KeyError:
					print "Cannot find artist or album."
				break
			if case(self.QF_ADDTRA):
				try:
					album = m_client.library[args[1]][args[2]]
					found = False
					for song in album:
						if song["title"] == args[3]:
							m_player.addToQueue(song)
							found = True
							break
					if found:
						print "Added {0} from {1} by {2} to queue".format(args[3], args[2], args[1])
					else:
						print "Cannot find artist, album or track."
				except KeyError:
					print "Cannot find artist, album or track."
				break
			if case():
				print "Argument error."
	
	def listHandler(self, args):
		global m_client
		content_mode = 0
		offset = 0
		try:
			page_no = int(args[1])
		except IndexError:
			page_no = 1
		except ValueError:
			page_no = 1
			offset = -1
		try:
			if args[2 + offset].upper() == "PLIST":
				try:
					playlist = args[3 + offset]
					content_mode = self.CON_PLTRACKS
				except IndexError:
					content_mode = self.CON_PLISTS
			else:
				artist = args[2 + offset]
				try:
					album = args[3 + offset]
					content_mode = self.CON_TRACKS
				except IndexError:
					content_mode = self.CON_ALBUMS
		except IndexError:
			content_mode = self.CON_ARTISTS
		lower_bound = (page_no - 1) * self.SINGLE_PG_LEN
		upper_bound = page_no * self.SINGLE_PG_LEN
		display_content = None
		fault = False
		for case in switch(content_mode):
			if case(self.CON_PLISTS):
				display_content = m_client.playlists.keys()
				print "All Playlists (page {0}/{1}):".format(page_no, ((len(display_content) / self.SINGLE_PG_LEN) + 1))
				break
			if case(self.CON_PLTRACKS):
				try:
					display_content = m_client.playlists[playlist]
					print "Tracks in {0} playlist (page {1}/{2}):".format(playlist, page_no, ((len(display_content) / self.SINGLE_PG_LEN) + 1))
				except:
					print "Cannot find artist or album."
					fault = True
				break
			if case(self.CON_ARTISTS):
				display_content = m_client.library.keys()
				print "All Artists (page {0}/{1}):".format(page_no, ((len(display_content) / self.SINGLE_PG_LEN) + 1))
				break
			if case(self.CON_ALBUMS):
				try:
					display_content = m_client.library[artist].keys()
					print "All albums by {0} (page {1}/{2}):".format(artist, page_no, ((len(display_content) / self.SINGLE_PG_LEN) + 1))
				except KeyError:
					print "Cannot find artist or album."
					fault = True
				break
			if case(self.CON_TRACKS):
				try:
					display_content = m_client.library[artist][album]
					print "All tracks in {0} by {1} (page {2}/{3}):".format(album, artist, page_no, ((len(display_content) / self.SINGLE_PG_LEN) + 1))
				except KeyError:
					print "Cannot find artist or album."
					fault = True
				break
		if not fault:
			display_content.sort()
			for i in range(lower_bound, upper_bound):
				try:
					item = display_content[i]
					if type(item) is dict:
						print item["title"].encode("utf-8")
					else:
						print item.encode("utf-8")
				except IndexError:
					pass
	
	def pmHandler(self, args):
		global m_player
		play_mode = 0
		if len(args) > 1:
			try:
				if args[1].upper() == "RANDOM":
					play_mode += 1
				if args[2].upper() == "REPEAT":
					play_mode += 2
				m_player.play_mode = play_mode
			except IndexError:
				print "Argument error!"
		for case in switch(m_player.play_mode):
			if case(0):
				print "Play mode: Linear, No Repeat"
				break
			if case(1):
				print "Play mode: Random, No Repeat"
				break
			if case(2):
				print "Play mode: Linear, Repeat"
				break
			if case(3):
				print "Play mode: Random, Repeat"
				break

def cl_print(console_string, *args):
	print console_string

def main():
	global m_player
	global m_client
	global last_fm
	global clh
	title_string = "\x1b]2;Google Play Music\x07"
	sys.stdout.write(title_string)
	print "Logging in to Google Play Music..."
	m_client = gMusicClient("GOOGLE_USER", "GOOGLE_PASS")
	print "Logging in to Last.fm..."
	last_fm = lastfmScrobbler("LASTFM_USER", "LASTFM_PASS", False)
	print "Creating GStreamer player..."
	m_player = mediaPlayer()
	print "Updating local library from Google Play Music..."
	m_client.updateLocalLib()
	clh = commandLineHandler()
	print "Ready!"
	print ""
	global run
	while run:
		clh.parseCL(raw_input())
	thread.exit()

gobject.threads_init()
main()
