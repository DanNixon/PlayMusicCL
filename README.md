PlayMusicCL
===========

A command line client for Google Play Music.

[![Code Health](https://landscape.io/github/DanNixon/PlayMusicCL/master/landscape.png)](https://landscape.io/github/DanNixon/PlayMusicCL/master)

Install/Configuration
---------------------

Install using ```python setup.py install```, this installs the majority of
dependencies, however you will also need the Python GTK bindings (for GST) which
can be installed on Debina basded systems with ```sudo apt-get install
python-gst*```.

Configuration is done in the ```.playmusicclrc``` file stored in the home
directory (see example), the ```google_user``` and ```google_device_id``` are
the minimum required keys for the app to function.  Password configs can be
omitted and the password requested when the app starts.

Omitting the ```lastfm_user``` config will disable Last.fm integration.

Usage
-----

From a terminal: ```playmusiccl```

Once the app is running you will then have access to the following commands:

-	```PLAY``` - Pauses or unpauses playback
-	```PAUSE``` - Same as ```PLAY```
- ```P``` - Same as ```PLAY```
-	```LIKE``` - Loves the current song on Last.fm and gives it a Thumbs Up on
	Google Play
-	```LOVE``` - Same as ```LIKE```
- ```L``` - Same as ```LIKE```
-	```EXIT``` - Exits
-	```NOW``` - Shows the title and artist of the currently playing song.
- ```[return]``` - Same as ```NOW```
-	```NEXT (n)``` - Plays the nth song after the current song (n has no effect in
	random play mode, n can also be negative to skip back through tracks)
- ```N``` - Plays next track
-	```PMODE [random/linear] [repeat/norepeat]``` - Specifies play options, if you
	have used any other media player they should be self explanatory
-	```LIST (pn)``` - Shows a list of all artists
-	```LIST (pn) PLIST``` - Shows a lit of all user playlists
-	```LIST (pn) PLIST [playlist]``` - Shows all songs in specified user playlist
-	```LIST (pn) [artist]``` - Shows all albums by specifies artist (including
	albums they appear on)
-	```LIST (pn) [artist] [album]``` - Shows all songs in specified album by
	specified artist
-	```QUEUE (pn)``` - Show songs currently in the queue (in the order they are to
	be played)
-	```QUEUE PLIST [playlist]``` - Add all songs from specified user playlist to
	queue
-	```QUEUE [artist]``` - Adds all songs by specified artist to queue
-	```QUEUE [artist] [album]``` - Adds all songs by specified album to queue
-	```QUEUE [artist] [album] [song]``` - Adds specified song to queue
- ```CLEARQUEUE``` - Stops playback and removes all songs from the queue
- ```PAM``` - "Play Awesome Music": clears queue, queues "Thumbs Up" playlist,
  sets random playback and plays

Note that ```n``` and ```pn``` are optional parameters and both default to 1,
```pn``` denotes the number of the page to display.

Commands themselves are case insensitive, however artist, album, track and
playlist names are case sensitive and must have correct spacing.

Command Examples
----------------

To see all albums by Eluvietie: ```list Eluveitie```

To see all tracks in Spirit by Eluveitie: ```list Eluveitie Spirit```

To add "...Of Fire, Wind and Wisdom" (in album Spirit) by Eluveitie to the
queue: ```queue Eluveitie Spirit "...Of Fire, Wind and Wisdom"```

To see all playlists: ```list plist```

To see all tracks in playlist "Symphonic Metal": ```list plist "Symphonic
Metal"```

To add all tracks from playlist "Symphonic Metal" to queue: ```queue plist
"Symphonic Metal"```
