#!/usr/bin/python
# -*- coding: utf_8 -*-

# Command line client for Google Play Music


import thread, time, shlex, random, sys, os, readline, atexit
from gmusicapi import Mobileclient
from getpass import getpass
import glib
import gst

__MusicClient__ = None
__MediaPlayer__ = None
__LastFm__ = None
__CLH__ = None

__Run__ = True


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

class GPMClient(object):
    all_songs_album_title = "All Songs"
    thumbs_up_playlist_name = "Thumbs Up"

    def __init__(self, email, password, device_id):
        self.__api = Mobileclient()
        self.logged_in = False
        self.__device_id = device_id

        attempts = 0
        while not self.logged_in and attempts < 3:
            self.logged_in = self.__api.login(email, password, device_id)
            attempts += 1

        self.all_tracks = dict()
        self.playlists = dict()
        self.library = dict()

    def logout(self):
        self.__api.logout()

    def update_local_lib(self):
        songs = self.__api.get_all_songs()
        self.playlists[self.thumbs_up_playlist_name] = list()

        # Get main library
        song_map = dict()
        for song in songs:
            if "rating" in song and song["rating"] == "5":
                self.playlists[self.thumbs_up_playlist_name].append(song)

            song_id = song["id"]
            song_artist = song["artist"]
            song_album = song["album"]

            song_map[song_id] = song

            if song_artist == "":
                song_artist = "Unknown Artist"

            if song_album == "":
                song_album = "Unknown Album"

            if not (song_artist in self.library):
                self.library[song_artist] = dict()
                self.library[song_artist][self.all_songs_album_title] = list()

            if not (song_album in self.library[song_artist]):
                self.library[song_artist][song_album] = list()

            self.library[song_artist][song_album].append(song)
            self.library[song_artist][self.all_songs_album_title].append(song)

        # Sort albums by track number
        for artist in self.library.keys():
            for album in self.library[artist].keys():
                if album == self.all_songs_album_title:
                    sorted_album = sorted(self.library[artist][album], key=lambda k: k['title'])
                else:
                    sorted_album = sorted(self.library[artist][album], key=lambda k: k.get('trackNumber', 0))
                self.library[artist][album] = sorted_album

        # Get all playlists
        plists = self.__api.get_all_user_playlist_contents()
        for plist in plists:
            plist_name = plist["name"]
            self.playlists[plist_name] = list()
            for track in plist["tracks"]:
                if not track["trackId"] in song_map:
                    song = song_map[track["trackId"]] = track["track"]
                    song["id"] = track["trackId"]
                else:
                    song = song_map[track["trackId"]]
                self.playlists[plist_name].append(song)

    def get_stream_url(self, song):
        return self.__api.get_stream_url(song["id"], self.__device_id)

    def rate_song(self, song, rating):
        try:
            song["rating"] = rating
            song_list = [song]
            self.__api.change_song_metadata(song_list)
            print "Gave a Thumbs Up to {0} by {1} on Google Play.".format(song["title"].encode("utf-8"), song["artist"].encode("utf-8"))
        except:
            print "Error giving a Thumbs Up on Google Play."

class MediaPlayer(object):
    def __init__(self):
        self.__player = None

        self.now_playing_song = None
        self.queue = list()
        self.queue_index = -1
        self.play_mode = 0

        thread.start_new_thread(self.player_thread, ())

    def __del__(self):
        self.now_playing_song = None
        self.__player.set_state(gst.STATE_NULL)

    def player_thread(self):
        if self.__player is None:
            self.__player = gst.element_factory_make("playbin2", "player")
            self.__player.set_state(gst.STATE_NULL)
            bus = self.__player.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self.handle_song_end)
            glib.MainLoop().run()

    def handle_song_end(self, _, message):
        if message.type == gst.MESSAGE_EOS:
            self.next(1)

    def clear_queue(self):
        self.stop()
        self.queue = list()
        self.queue_index = -1

    def print_current_song(self):
        song = self.now_playing_song
        if song is not None:
            track = __MediaPlayer__.now_playing_song["title"]
            artist = __MediaPlayer__.now_playing_song["artist"]
            print "Now playing {0} by {1}".format(track.encode("utf-8"), artist.encode("utf-8"))
        else:
            print "No song playing."

    def set_terminal_title(self):
        if self.now_playing_song is None or self.__player.get_state()[1] == gst.STATE_PAUSED:
            sys.stdout.write("\x1b]2;Google Play Music\x07")
            return
        title_string = "\x1b]2;{0} - {1}\x07".format(self.now_playing_song["title"].encode("utf-8"),
                                                     self.now_playing_song["artist"].encode("utf-8"))
        thread.start_new_thread(cl_print, (title_string, 1))


    def play(self, song):
        song_url = __MusicClient__.get_stream_url(song)
        try:
            self.__player.set_property("uri", song_url)
            self.__player.set_state(gst.STATE_PLAYING)
            self.now_playing_song = song
            self.print_current_song()
            self.set_terminal_title()
            __LastFm__.update_now_playing(song)
        except AttributeError:
            print "Player error!"

    def toggle_playback(self):
        try:
            player_state = self.__player.get_state()[1]
            if player_state == gst.STATE_PAUSED:
                self.__player.set_state(gst.STATE_PLAYING)
                self.set_terminal_title()
                print "Resumng playback."
            elif player_state == gst.STATE_PLAYING:
                self.__player.set_state(gst.STATE_PAUSED)
                self.set_terminal_title()
                print "Pauseing playback."
                print ""
            elif player_state == gst.STATE_NULL:
                self.__play_next_in_queue(1)
        except AttributeError:
            print "Player error!"

    def stop(self):
        try:
            self.__player.set_state(gst.STATE_NULL)
            self.now_playing_song = None
        except AttributeError:
            print "Player error!"


    def __play_next_in_queue(self, n_offset):
        if (self.play_mode % 2) == 0:
            self.queue_index += n_offset
        else:
            self.queue_index = random.randint(0, (len(self.queue) - 1))
        if (self.queue_index < len(self.queue)) and (self.queue_index >= 0):
            next_song = self.queue[self.queue_index]
            self.play(next_song)
        else:
            if (self.play_mode == 2) or (self.play_mode == 3):
                self.queue_index = -1
                self.__play_next_in_queue(1)
            else:
                self.stop()
                self.set_terminal_title()

    def add_to_queue(self, song):
        self.queue.append(song)

    def next(self, n_offset):
        __LastFm__.scrobble(self.now_playing_song)
        self.stop()
        self.__play_next_in_queue(n_offset)

class LastfmScrobbler(object):
    def __init__(self, username, password, use):
        self.__api_key = "a0790cb91b8799b0eda1f60d3924b676"
        self.__api_secret = "5007f138c5fef4278f36c70d760f24b7"

        self.__session = None

        if use:
            import pylast
            password_hash = pylast.md5(password)
            self.__session = pylast.LastFMNetwork(api_key = self.__api_key,
                                                  api_secret = self.__api_secret,
                                                  username = username,
                                                  password_hash = password_hash)
        self.enabled = use

    def love_song(self, song):
        if song is not None and self.enabled:
            print "Loving {0} by {1} on Last.fm.".format(song["title"].encode("utf-8"),
                                                         song["artist"].encode("utf-8"))
            thread.start_new_thread(self.__love, (song,))
        else:
            print "No song playing or Last.fm disabled."

    def __love(self, song):
        title = song['title']
        artist = song['artist']
        if artist == "":
            artist = "Unknown Artist"
        try:
            track = self.__session.get_track(artist, title)
            track.love()
        except:
            print "Error loving song on Last.fm"

    def update_now_playing(self, song):
        if song is not None and self.enabled:
            thread.start_new_thread(self.__now_playing, (song,))

    def __now_playing(self, song):
        title = song['title']
        artist = song['artist']
        if artist == "":
            artist = "Unknown Artist"
        try:
            self.__session.update_now_playing(artist, title)
        except:
            pass

    def scrobble(self, song):
        if song is not None and self.enabled:
            thread.start_new_thread(self.__scrobble, (song,))

    def __scrobble(self, song):
        title = song['title']
        artist = song['artist']
        if artist == "":
            artist = "Unknown Artist"
        try:
            self.__session.scrobble(artist, title, int(time.time()))
        except:
            pass

class CommandCompleter(object):
    def __init__(self, library, playlists):
        self.__library = library
        self.__playlists = playlists
        self.__basic_commands = ["play", "pause", "like", "love", "exit", "now", "next", "pmode", "list", "queue", "pam", "clearqueue"]

    def complete(self, _, state):
        response = None
        if state == 0:
            origline = readline.get_line_buffer()
            begin = readline.get_begidx()
            end = readline.get_endidx()
            being_completed = origline[begin:end]
            words = origline.split()

            if not words:
                self.current_candidates = sorted(self.__basic_commands)
            else:
                try:
                    # Get list of all possible candidates based on previous complete input
                    if begin == 0:
                        # Match list of commands
                        candidates = self.__basic_commands
                    else:
                        # Match based on previous commands
                        candidates = []
                        for case in switch(words[0].upper()):
                            # Add candidates for queueing or listing stuff
                            if case("QUEUE") or case("LIST"):
                                finished_words_len = len(words)
                                if being_completed:
                                    finished_words_len -= 1

                                for case in switch(finished_words_len):
                                    # Listing/queueing artists (or the playlist selection command)
                                    if case(1):
                                        candidates = sorted(self.__library.keys())
                                        candidates.insert(0, "plist")
                                        break
                                    # Listing/queueing albums or playlists
                                    if case(2):
                                        if words[1].upper() == "PLIST":
                                            candidates = sorted(self.__playlists.keys())
                                        else:
                                            candidates = sorted(self.__library[words[1]].keys())
                                        break
                                    # Queueing tracks
                                    if case(3):
                                        if words[0].upper() == "QUEUE":
                                            candidates = sorted([s['title'] for s in self.__library[words[1]][words[2]]])
                                        break
                                break
                            # Add candidates for play mode selection
                            if case("PMODE"):
                                for case in switch(len(words)):
                                    if case(1):
                                        candidates = ["random", "linear"]
                                        break
                                    if case(2):
                                        candidates = ["repeat", "norepeat"]
                                        break

                    # Filter possible candidates based on partial completion
                    if being_completed:
                        # Match options with portion of input being completed
                        self.current_candidates = [c.replace(r' ', r'\ ') for c in candidates if c.startswith(being_completed)]
                    else:
                        # Matching empty string so use all candidates
                        self.current_candidates = [c.replace(r' ', r'\ ') for c in candidates]
                except (KeyError, IndexError), _:
                    self.current_candidates = []

        try:
            response = self.current_candidates[state]
        except IndexError:
            response = None
        return response

class CommandLineHandler(object):
    __CON_PLISTS = 1
    __CON_PLTRACKS = 2
    __CON_ARTISTS = 3
    __CON_ALBUMS = 4
    __CON_TRACKS = 5

    __QF_LIST = 1
    __QF_ADDPLI = 2
    __QF_ADDART = 3
    __QF_ADDALB = 4
    __QF_ADDTRA = 5

    __SINGLE_PG_LEN = 20

    def __init__(self, history_filename, media_client):
        history_file = os.path.expanduser(history_filename)
        try:
            readline.read_history_file(history_file)
        except IOError:
            pass
        atexit.register(readline.write_history_file, history_file)

        readline.parse_and_bind('tab: complete')
        readline.parse_and_bind('set editing-mode vi')
        readline.set_completer(CommandCompleter(media_client.library, media_client.playlists).complete)

    def __del__(self):
        title_string = "\x1b]2;I played music once, but then I took a SIGTERM to the thread.\x07"
        sys.stdout.write(title_string)

    def parse_cl(self, in_string):
        if len(in_string) is 0:
            __MediaPlayer__.print_current_song()
            print ""
            return
        function = None
        try:
            args = shlex.split(in_string)
            function = args[0].upper()
        except IndexError:
            pass
        for case in switch(function):
            if case("LIST"):
                self.list_handler(args)
                print ""
                break
            if case("QUEUE"):
                self.queueHandler(args)
                print ""
                break
            if case("PAUSE"):
                __MediaPlayer__.toggle_playback()
                break
            if case("PLAY"):
                __MediaPlayer__.toggle_playback()
                break
            if case("P"):
                self.parse_cl("PLAY")
                return
            if case("LIKE"):
                __LastFm__.love_song(__MediaPlayer__.now_playing_song)
                __MusicClient__.rate_song(__MediaPlayer__.now_playing_song, 5)
                print ""
                break
            if case("LOVE"):
                self.parse_cl("LIKE")
                return
            if case("L"):
                self.parse_cl("LIKE")
                return
            if case("PMODE"):
                self.pm_handler(args)
                print ""
                break
            if case("NEXT"):
                try:
                    n_offset = int(args[1])
                except ValueError:
                    n_offset = 1
                except IndexError:
                    n_offset = 1
                __MediaPlayer__.next(n_offset)
                break
            if case("N"):
                self.parse_cl("NEXT")
                return
            if case("NOW"):
                __MediaPlayer__.print_current_song()
                print ""
                break
            if case("CLEARQUEUE"):
                __MediaPlayer__.clear_queue()
                print "Queue cleared"
                __MediaPlayer__.set_terminal_title()
                print ""
                break
            if case("PAM"):
                print "Playing awesome music"
                __MediaPlayer__.clear_queue()
                for song in __MusicClient__.playlists["Thumbs Up"]:
                    __MediaPlayer__.add_to_queue(song)
                __MediaPlayer__.play_mode = 3
                __MediaPlayer__.next(1)
                break
            if case("EXIT"):
                print "じゃね"
                global __Run__
                __Run__ = False
                break
            if case():
                print "Argument error!"
                print ""

    def queueHandler(self, args):
        function = 0
        page_no = 0
        for case in switch(len(args)):
            if case(1):
                function = self.__QF_LIST
                page_no = 1
                break
            if case(2):
                try:
                    page_no = int(args[1])
                    function = self.__QF_LIST
                except ValueError:
                    function = self.__QF_ADDART
                break
            if case(3):
                if args[1].upper() == "PLIST":
                    function = self.__QF_ADDPLI
                else:
                    function = self.__QF_ADDALB
                break
            if case(4):
                function = self.__QF_ADDTRA
                break
        for case in switch(function):
            if case(self.__QF_LIST):
                queue = __MediaPlayer__.queue
                print "Tracks in queue (page {0}/{1})".format(page_no, ((len(queue) / self.__SINGLE_PG_LEN) + 1))
                lower_bound = (page_no - 1) * self.__SINGLE_PG_LEN
                upper_bound = page_no * self.__SINGLE_PG_LEN
                for i in range(lower_bound, upper_bound):
                    try:
                        print "{0} - {1}".format(queue[i]["artist"].encode("utf-8"), queue[i]["title"].encode("utf-8"))
                    except IndexError:
                        pass
                break
            if case(self.__QF_ADDPLI):
                try:
                    playlist = __MusicClient__.playlists[args[2]]
                    for song in playlist:
                        __MediaPlayer__.add_to_queue(song)
                    print "Added {0} tracks from {1} to queue".format(len(playlist), args[2])
                except KeyError:
                    print "Cannot find playlist."
                break
            if case(self.__QF_ADDART):
                try:
                    artist = __MusicClient__.library[args[1]]
                    count = 0
                    for album in artist:
                        for song in artist[album]:
                            __MediaPlayer__.add_to_queue(song)
                            count += 1
                    print "Added {0} tracks by {1} to queue".format(count, args[1])
                except KeyError:
                    print "Cannot find artist."
                break
            if case(self.__QF_ADDALB):
                try:
                    album = __MusicClient__.library[args[1]][args[2]]
                    count = 0
                    for song in album:
                        __MediaPlayer__.add_to_queue(song)
                        count += 1
                    print "Added {0} tracks from {1} by {2} to queue".format(count, args[2], args[1])
                except KeyError:
                    print "Cannot find artist or album."
                break
            if case(self.__QF_ADDTRA):
                try:
                    album = __MusicClient__.library[args[1]][args[2]]
                    found = False
                    for song in album:
                        if song["title"] == args[3]:
                            __MediaPlayer__.add_to_queue(song)
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

    def list_handler(self, args):
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
                    content_mode = self.__CON_PLTRACKS
                except IndexError:
                    content_mode = self.__CON_PLISTS
            else:
                artist = args[2 + offset]
                try:
                    album = args[3 + offset]
                    content_mode = self.__CON_TRACKS
                except IndexError:
                    content_mode = self.__CON_ALBUMS
        except IndexError:
            content_mode = self.__CON_ARTISTS
        lower_bound = (page_no - 1) * self.__SINGLE_PG_LEN
        upper_bound = page_no * self.__SINGLE_PG_LEN
        display_content = None
        fault = False
        for case in switch(content_mode):
            if case(self.__CON_PLISTS):
                display_content = sorted(__MusicClient__.playlists.keys())
                print "All Playlists (page {0}/{1}):".format(page_no, ((len(display_content) / self.__SINGLE_PG_LEN) + 1))
                break
            if case(self.__CON_PLTRACKS):
                try:
                    display_content = __MusicClient__.playlists[playlist]
                    print "Tracks in {0} playlist (page {1}/{2}):".format(playlist, page_no, ((len(display_content) / self.__SINGLE_PG_LEN) + 1))
                except:
                    print "Cannot find artist or album."
                    fault = True
                break
            if case(self.__CON_ARTISTS):
                display_content = sorted(__MusicClient__.library.keys())
                print "All Artists (page {0}/{1}):".format(page_no, ((len(display_content) / self.__SINGLE_PG_LEN) + 1))
                break
            if case(self.__CON_ALBUMS):
                try:
                    display_content = sorted(__MusicClient__.library[artist].keys())
                    print "All albums by {0} (page {1}/{2}):".format(artist, page_no, ((len(display_content) / self.__SINGLE_PG_LEN) + 1))
                except KeyError:
                    print "Cannot find artist or album."
                    fault = True
                break
            if case(self.__CON_TRACKS):
                try:
                    display_content = __MusicClient__.library[artist][album]
                    print "All tracks in {0} by {1} (page {2}/{3}):".format(album, artist, page_no, ((len(display_content) / self.__SINGLE_PG_LEN) + 1))
                except KeyError:
                    print "Cannot find artist or album."
                    fault = True
                break
        if not fault:
            for i in range(lower_bound, upper_bound):
                try:
                    item = display_content[i]
                    if type(item) is dict:
                        print item["title"].encode("utf-8")
                    else:
                        print item.encode("utf-8")
                except IndexError:
                    pass

    def pm_handler(self, args):
        play_mode = 0
        if len(args) > 1:
            try:
                if args[1].upper() == "RANDOM":
                    play_mode += 1
                if args[2].upper() == "REPEAT":
                    play_mode += 2
                __MediaPlayer__.play_mode = play_mode
            except IndexError:
                print "Argument error!"
        for case in switch(__MediaPlayer__.play_mode):
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

def cl_print(console_string, _):
    print console_string

def get_config():
    config = dict()
    try:
        with open(os.path.expanduser("~/.playmusicclrc")) as conf_file:
            conf_lines = conf_file.readlines()
            for line in conf_lines:
                data = line.split()
                if len(data) > 1:
                    for case in switch(data[0]):
                        if case("google_user"):
                            config['google_user'] = data[1]
                            break
                        if case("google_pass"):
                            config['google_pass'] = data[1]
                            break
                        if case("google_deviceid"):
                            config['google_deviceid'] = data[1]
                            break
                        if case("lastfm_user"):
                            config['lastfm_user'] = data[1]
                            break
                        if case("lastfm_pass"):
                            config['lastfm_pass'] = data[1]
                            break
                        if case("history_file"):
                            config["history_file"] = data[1]
                            break;

        if "history_file" not in config:
            config["history_file"] = "~/.playmusiccl_history"
        if "google_pass" not in config:
            config["google_pass"] = getpass("Google password: ")
        if "lastfm_pass" not in config and "lastfm_user" in config:
            config["lastfm_pass"] = getpass("Last.fm password: ")
        # if ["google_user", "google_pass", "google_deviceid"] not in config:
            # print "Config file error"
            # sys.exit(1)
    except IOError:
        print "Can't find ~/.playmusicclrc"
        sys.exit(1);
    return config

def main():
    global __MusicClient__
    global __LastFm__
    global __MediaPlayer__
    global __CLH__
    global __Run__
    title_string = "\x1b]2;Google Play Music\x07"
    sys.stdout.write(title_string)

    config = get_config()

    print "Logging in to Google Play Music..."
    __MusicClient__ = GPMClient(config.get("google_user"), config.get("google_pass"), config.get("google_deviceid"))

    if("lastfm_user" in config):
        print "Logging in to Last.fm..."
    __LastFm__ = LastfmScrobbler(config.get("lastfm_user", ""), config.get("lastfm_pass", ""), ("lastfm_user" in config))

    print "Creating GStreamer player..."
    __MediaPlayer__ = MediaPlayer()

    print "Updating local library from Google Play Music..."
    __MusicClient__.update_local_lib()
    __CLH__ = CommandLineHandler(config["history_file"], __MusicClient__)

    print "Ready!"
    print ""
    __Run__ = True
    while __Run__:
        __CLH__.parse_cl(raw_input())

    __MusicClient__.logout()

    thread.exit()
