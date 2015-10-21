from playmusiccl import *

from gi.repository import GObject, Gst

def run():
	GObject.threads_init()
	Gst.init(None)
	main()
