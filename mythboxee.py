import mc
import re
import sys
import random
import time
import md5
import pickle
import mythtv
import threading
from ttvdb import tvdb_api
from mythtv import MythError
from operator import itemgetter, attrgetter

"""
MythBoxeeBase is the base class for which the majority of classes
within the app inherit. It sets up the connection to the database
and takes care of some other basic functions.
"""
class MythBoxeeBase:
	logLevel = 1
	version = "4.4.23.1.beta"
	tvdb_apikey = "6BEAB4CB5157AAE0"
	be = None
	db = None
	recs = None
	titles = []
	recordings = []
	banners = {}
	shows = {}
	series = {}
	
	def __init__(self):
		self.log("def(__init__): Start =========================================================")
		self.log("def(__init__): Version: " + self.version)
		self.log("def(__init__): Python Version: " + str(sys.version_info))

		self.config = mc.GetApp().GetLocalConfig()

		# Set the version on any page that loads
		mc.GetActiveWindow().GetLabel(1013).SetLabel(self.version)

		# We'll use this to determine when to reload data.
		#self.config.SetValue("LastRunTime", str(time.time()))
		#self.config.SetValue("CurrentShowItemID", "0")

		# If this is the first time the app is being run, lets set some default options.
		if not self.config.GetValue("app.firstrun"):
			self.config.SetValue("SortBy", "Original Air Date")
			self.config.SetValue("SortDir", "Descending")
			self.config.SetValue("Filter", "All")
			self.config.SetValue("StreamMethod", "XML")
			self.config.SetValue("app.firstrun", "true")

		# If dbconn isn't set, we'll assume we haven't found the backend.
		if not self.config.GetValue("dbconn"):
			self.config.SetValue("loadingmain", "true")
			mc.ActivateWindow(14004)
		else:
			# Now that the backend has been discovered, lets connect.
			try:
				self.log("def(__init__): Attempting Database Connection ...")
				self.dbconf = eval(self.config.GetValue("dbconn"))
				self.db = mythtv.MythDB(**self.dbconf)
			except MythError, e:
				self.log("def(__init__): Error: " + e.message)
				mc.ShowDialogNotification("Failed to connect to the MythTV Backend")
				mc.ActivateWindow(14004)
			else:
				self.log("def(__init__): Database Connection Successful")
				self.be = mythtv.MythBE(db=self.db)

		if self.config.GetValue("cache.titles"):
			self.titles = pickle.loads(self.config.GetValue("cache.titles"))
		if self.config.GetValue("cache.banners"):
			self.banners = pickle.loads(self.config.GetValue("cache.banners"))
		if self.config.GetValue("cache.series"):
			self.series = pickle.loads(self.config.GetValue("cache.series"))
		if self.config.GetValue("cache.shows"):
			self.shows = pickle.loads(self.config.GetValue("cache.shows"))

		self.log("def(__init__): End ===========================================================")

	"""
	DiscoverBackend - just as it sounds

	Attempt to discover the MythTV Backend using UPNP protocol, once found
	try and gather MySQL database connection information using default PIN
	via the XML interface. If that fails then prompt user to enter their
	custom SecurityPin, if we fail to gather database information that way
	finally prompt user to enter their credentials manually.
	"""
	def DiscoverBackend(self):
		self.log("def(DiscoverBackend): Start =========================================================")

		pin = self.config.GetValue("pin")
		dbconn = self.config.GetValue("dbconn")

		if not pin:
			pin = 0000

		try:
			self.log("def(DiscoverBackend): Attempting Database Connection ...")
			self.db = mythtv.MythDB(SecurityPin=pin)
		except Exception, e:
			self.log("def(DiscoverBackend): Exception: " + str(e.ename))
			self.log("def(DiscoverBackend): End ===========================================================")
			return False
		else:
			# We have a successful connection, save database information
			self.config.SetValue("dbconn", str(self.db.dbconn))

			self.log("def(DiscoverBackend): Database Connection Successful")
			self.log("def(DiscoverBackend): End ===========================================================")
			return True

	"""
	log - logging function mainly for debugging
	"""
	def log(self, message):
		if self.logLevel == 3:
			mc.ShowDialogNotification(message)

		if self.logLevel >= 2:
			mc.LogDebug(">>> MythBoxee: " + message)

		if self.logLevel == 1:
			mc.LogInfo(">>> MythBoxee: " + message)
			print ">>> MythBoxee: " + message

class MythBoxeeLogger:
	logLevel = 1

	"""
	log - logging function mainly for debugging
	"""
	def log(self, message):
		if self.logLevel == 3:
			mc.ShowDialogNotification(message)

		if self.logLevel >= 2:
			mc.LogDebug(">>> MythBoxee: " + message)

		if self.logLevel == 1:
			mc.LogInfo(">>> MythBoxee: " + message)
			print ">>> MythBoxee: " + message
	

class MythBoxeeReactor(threading.Thread):
	reactorName = "MythBoxeeReactor"

	def __init__(self, name):
		self.reactorName = name
		self._stopEvent = threading.Event()
		self._sleepPeriod = 10
		threading.Thread.__init__(self, name=self.reactorName)

	def stop(self,timeout=None):
		self._stopEvent.set()
		threading.Thread.join(self,timeout)


class MythBoxeeRecordings(MythBoxeeBase, MythBoxeeReactor):
	recs = None
	titles = []
	recordings = []
	banners = {}
	shows = {}
	series = {}

	def __init__(self):
		MythBoxeeBase.__init__(self)
		MythBoxeeReactor.__init__(self, "MythBoxeeRecordings")

		if self.config.GetValue("cache.banners"):
			self.banners = pickle.loads(self.config.GetValue("cache.banners"))
		if self.config.GetValue("cache.series"):
			self.series = pickle.loads(self.config.GetValue("cache.series"))
			
	"""
	run - this is called automatically when the thread is started
	"""
	def run(self):
		self.log("%s starts" % (self.getName(),))
		while not self._stopEvent.isSet():
			self.log("%s ran" % (self.getName(),))

			## Do Stuff Here
			self._GetDbRecordings()

			## Sleep
			self._stopEvent.wait(self._sleepPeriod)
			
	"""
	GetRecordings - Interface to pull recording information for use in the app.
	"""
	def GetRecordings(self):
		cacheTime = self.config.GetValue("cache.time")
		if not cacheTime or cacheTime <= str(time.time() - 600):
			## pull from database
			self._GetDbRecordings()
			#self.SetShows()
		else:
			## pull from cache
			self._GetCacheRecordings()
			if len(mc.GetWindow(14001).GetList(1030).GetItems()) == 0:
				self.SetShows()


	"""
	_GetCacheRecordings - Pulls recording information from the local cache
	"""
	def _GetCacheRecordings(self):
		self.log("def(_GetCacheRecordings): Start =========================================================")
		## Load information from cache
		self.titles = pickle.loads(self.config.GetValue("cache.titles"))
		self.banners = pickle.loads(self.config.GetValue("cache.banners"))
		self.series = pickle.loads(self.config.GetValue("cache.series"))
		self.shows = pickle.loads(self.config.GetValue("cache.shows"))
		self.titles.sort()
		self.log("def(_GetCacheRecordings): End ===========================================================")


	"""
	_GetDbRecordings - Pulls all of the recordings out of the backend and prepares them for use in the app.
	"""
	def _GetDbRecordings(self):
		self.log("def(_GetDbRecordings): Start =========================================================")

		t = tvdb_api.Tvdb(apikey=self.tvdb_apikey)

		titles = []
		banners = {}
		series = {}
		shows = {}

		self.recs = self.be.getRecordings()

		# Generate the the Fingerprint
		finger_titles = []
		for rec in self.recs:
			if rec.title not in finger_titles:
				finger_titles.append(str(rec.title))
		finger_titles.sort()

		fingerprint = str(md5.new(str(finger_titles)).hexdigest())
		
		self.log("def(_GetDbRecordings): " + fingerprint)
		
		if self.config.GetValue("cache.fingerprint") == fingerprint:
			self.log("def(_GetDbRecordings): Fingerprint Matches, Retrieving Recordings from the Cache")
			self._GetCacheRecordings()
		else:
			self.log("def(_GetDbRecordings): New Fingerprint, Retrieving Recordings from the Database")
			self.config.SetValue("cache.fingerprint", fingerprint)

			x = 0
			for recording in self.recs:
				if recording.title not in titles:
					titles.append(str(recording.title))
					shows[str(recording.title)] = []

				# Check to see if we have a valid banner for the show, if not try and get one.
				if recording.title not in self.banners:
					self.banners[str(recording.title)] = self.GetRecordingArtwork(str(recording.title))
				else:
					if self.banners[str(recording.title)] == "mb_artwork_error.png":
						self.banners[str(recording.title)] = self.GetRecordingArtwork(str(recording.title))

				# Check to see if we have a valid series id for the show, if not try and get one.
				if recording.title not in self.series:
					self.series[str(recording.title)] = self.GetRecordingSeriesID(str(recording.title))
				else:
					if self.series[str(recording.title)] == 00000:
						self.series[str(recording.title)] = self.GetRecordingSeriesID(str(recording.title))

				# Check for title, and if not encode it utf-8
				if recording.title == None:
					title = ""
				else:
					title = recording.title.encode('utf-8')

				# Check for subtitle, and if not encode it utf-8
				if recording.subtitle == None:
					subtitle = ""
				else:
					subtitle = recording.subtitle.encode('utf-8')

				# Check for description, and if not encode it utf-8
				if recording.description == None:
					description = ""
				else:
					description = recording.description.encode('utf-8')

				single = [title, subtitle, description, str(recording.chanid), str(recording.airdate), str(recording.starttime), str(recording.endtime), recording.getRecorded().watched, x]
				shows[str(recording.title)].append(single)
				x = x + 1

			## Set our global variables
			self.titles = titles
			self.shows = shows
			
			self.titles.sort()

			# Lets cache our findings for now and the time we cached them.
			self.config.SetValue("cache.time", str(time.time()))
			self.config.SetValue("cache.titles", pickle.dumps(titles))
			self.config.SetValue("cache.titlecount", str(len(titles)))
			self.config.SetValue("cache.banners", pickle.dumps(self.banners))
			self.config.SetValue("cache.series", pickle.dumps(self.series))
			self.config.SetValue("cache.shows", pickle.dumps(shows))
			self.config.SetValue("cache.changed", "true")

		self.log("def(GetRecordings): End ===========================================================")

	"""
	GetRecordingArtwork - Get the Artwork for a show.
	"""
	def GetRecordingArtwork(self, title):
		self.log("def(GetRecordingArtwork): Start =========================================================")

		tries = 4
		while tries > 0:
			try:
				t = tvdb_api.Tvdb(apikey=self.tvdb_apikey)
				artwork = t[title]['banner']
				tries = 0
			except:
				artwork = "mb_artwork_error.png"
				tries = tries - 1

		self.log("def(GetRecordingArtwork): URL: " + str(artwork))
		self.log("def(GetRecordingArtwork): End =========================================================")

		return artwork


	"""
	GetRecordingSeriesID - Get the Series ID of a show.

	TODO: rewrite this entire function
	"""
	def GetRecordingSeriesID(self, title):
		self.log("def(GetRecordingSeriesID): Start =========================================================")

		tries = 4
		while tries > 0:
			try:
				t = tvdb_api.Tvdb(apikey=self.tvdb_apikey)
				seriesid = t[title]['seriesid']
				tries = 0
			except:
				seriesid = 00000
				tries = tries - 1

		self.log("def(GetRecordingSeriesID): SeriesID: " + str(seriesid))
		self.log("def(GetRecordingSeriesID): End ===========================================================")
		return seriesid


class MythBoxeeMainUIUpdater(MythBoxeeReactor, MythBoxeeLogger):
	titles = []
	recordings = []
	banners = {}
	shows = {}
	series = {}

	def __init__(self):
		MythBoxeeReactor.__init__(self, "MythBoxeeMainUIUpdater")
		self.config = mc.GetApp().GetLocalConfig()
		self._sleepPeriod = 2
		
	def run(self):
		self.log("def(MythBoxeeMainUIUpdater.Run): Started")
		while not self._stopEvent.isSet():
			self.log("def(MythBoxeeMainUIUpdater.Run): Run")
			
			if self.config.GetValue("cache.titles"):
				self.titles = pickle.loads(self.config.GetValue("cache.titles"))
			if self.config.GetValue("cache.banners"):
				self.banners = pickle.loads(self.config.GetValue("cache.banners"))
			if self.config.GetValue("cache.series"):
				self.series = pickle.loads(self.config.GetValue("cache.series"))
			if self.config.GetValue("cache.shows"):
				self.shows = pickle.loads(self.config.GetValue("cache.shows"))

			if (len(mc.GetWindow(14001).GetList(1030).GetItems())) == 0 or self.config.GetValue("cache.changed") == "true":
				self.log("def(MythBoxeeMainUIUpdater.Run): Change!")
				self.config.SetValue("loadingmain", "true")
				self.SetShows()
				self.config.SetValue("cache.changed", "false")
			else:
				self.log("def(MythBoxeeMainUIUpdater.Run): No Change")
				
				## Put focus on last selected item
				if self.config.GetValue("CurrentShowItemID"):
					itemId = int(self.config.GetValue("CurrentShowItemID"))
					if itemId and itemId != 0:
						mc.GetWindow(14001).GetList(1030).SetFocusedItem(itemId)

				self.config.Reset("loadingmain")
				self._sleepPeriod = 10

			## Sleep
			self._stopEvent.wait(self._sleepPeriod)
			

	def SetShows(self):
		self.log("def(MythBoxeeMainUIUpdater.SetShows): Start =========================================================")

		items = mc.ListItems()
		for title in self.titles:
			self.log("def(SetShows): " + str(title))
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(str(title))
			item.SetThumbnail(self.banners[title])
			item.SetProperty("videos", str(len(self.shows[title])))
			item.SetProperty("seriesid", str(self.series[title]))
			items.append(item)
		mc.GetWindow(14001).GetList(1030).SetItems(items)

		## Put focus on last selected item
		#itemId = int(self.config.GetValue("CurrentShowItemID"))
		#if itemId and itemId != 0:
		#	mc.GetWindow(14001).GetList(1030).SetFocusedItem(itemId)
		
		if len(self.titles) > 0:
			self.config.Reset("loadingmain")

		self.log("def(MythBoxeeMainUIUpdater.SetShows): End ===========================================================")


class MythBoxeeShowUIUpdater(MythBoxeeReactor, MythBoxeeLogger):
	def __init__(self):
		MythBoxeeReactor.__init__(self, "MythBoxeeShowUIUpdater")
		self.config = mc.GetApp().GetLocalConfig()
		self.dbconf = eval(self.config.GetValue("dbconn"))
		self._sleepPeriod = 2

		if self.config.GetValue("cache.titles"):
			self.titles = pickle.loads(self.config.GetValue("cache.titles"))
		if self.config.GetValue("cache.banners"):
			self.banners = pickle.loads(self.config.GetValue("cache.banners"))
		if self.config.GetValue("cache.series"):
			self.series = pickle.loads(self.config.GetValue("cache.series"))
		if self.config.GetValue("cache.shows"):
			self.shows = pickle.loads(self.config.GetValue("cache.shows"))
		
	def run(self):
		print "MythBoxeeShowUIUpdater Started"
		while not self._stopEvent.isSet():
			print "MythBoxeeShowUIUpdater Ran"

			if len(mc.GetWindow(14002).GetList(2040).GetItems()) == 0 or self.config.GetValue("cache.changed") == "true":
				self.LoadShowRecordings()
				self.config.SetValue("cache.changed", "false")
			else:
				self.config.Reset("loading")
				self._sleepPeriod = 10

			## Sleep
			self._stopEvent.wait(self._sleepPeriod)

	"""
	LoadShowRecordings

	Determine which show is being displayed and find all the recordings for it.
	Then populate the recording list for the singular show for viewer to watch.
	"""
	def LoadShowRecordings(self):
		self.log("def(LoadShowRecordings): Start =========================================================")
		self.config.SetValue("loading", "true")

		title = self.config.GetValue("CurrentShowTitle")

		## Get current sort and filter settings
		sortBy = self.config.GetValue("SortBy")
		sortDir = self.config.GetValue("SortDir")
		theFilter = self.config.GetValue("Filter")

		self.log("def(LoadShowRecordings): Sort By:  " + sortBy)
		self.log("def(LoadShowRecordings): Sort Dir: " + sortDir)
		self.log("def(LoadShowRecordings): Filter:   " + theFilter)

		## Clear the episodes container
		episodes = None

		## Sort based on Sorting Criteria
		if sortBy == "Original Air Date" and sortDir == "Ascending":
			episodes = sorted(self.shows[title], key=itemgetter(4))
		elif sortBy == "Original Air Date" and sortDir == "Descending":
			episodes = sorted(self.shows[title], key=itemgetter(4), reverse=True)
		elif sortBy == "Recorded Date" and sortDir == "Ascending":
			episodes = sorted(self.shows[title], key=itemgetter(5))
		elif sortBy == "Recorded Date" and sortDir == "Descending":
			episodes = sorted(self.shows[title], key=itemgetter(5), reverse=True)
		elif sortBy == "Title" and sortDir == "Ascending":
			episodes = sorted(self.shows[title], key=itemgetter(1))
		elif sortBy == "Title" and sortDir == "Descending":
			episodes = sorted(self.shows[title], key=itemgetter(1), reverse=True)
		else:
			episodes = self.shows[title]

		self.config.SetValue("cache.episodecount", str(len(episodes)))

		## Loop through all our recordings, and add them to the list.
		showitems = mc.ListItems()
		for title,subtitle,desc,chanid,airdate,starttime,endtime,watched,ref in episodes:
			#recording = self.recs[ref]

			# Filter the Episodes
			if theFilter == "Watched" and watched == 0:
				continue
			elif theFilter == "Unwatched" and watched == 1:
				continue

			# Create the Item list and populate it
			showitem = mc.ListItem( mc.ListItem.MEDIA_VIDEO_EPISODE )
			showitem.SetLabel(subtitle)
			showitem.SetTitle(subtitle)
			showitem.SetTVShowTitle(title)
			showitem.SetDescription(desc)
			showitem.SetProperty("starttime", starttime)
			#showitem.SetProperty("ref", ref)

			## Sometimes dates aren't set, so generate one if not.
			try:
				date = airdate.split("-")
				showitem.SetDate(int(date[0]), int(date[1]), int(date[2]))
			except:
				showitem.SetDate(2010, 01, 01)


			# Determine Stream Method, Generate Proper Path
			streamMethod = self.config.GetValue("StreamMethod")
			if streamMethod == "XML":
				time = starttime.replace("T", "%20")
				path = "http://" + self.dbconf['DBHostName'] + ":6544/Myth/GetRecording?ChanId=" + chanid + "&StartTime=" + time
				showitem.SetThumbnail("http://" + self.dbconf['DBHostName'] + ":6544/Myth/GetPreviewImage?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", " "))
				showitem.SetPath(path)
			elif streamMethod == "SMB":
				time = starttime.replace("T", "").replace("-", "").replace(":", "").replace(" ","")
				path = "smb://" + self.config.GetValue("smb.username") + ":" + self.config.GetValue("smb.password") + "@" + self.dbconf["DBHostName"] + "/" + self.config.GetValue("smb.share") + "/" + chanid + "_" + time + ".mpg"
				showitem.SetThumbnail(path + ".png")
				showitem.SetPath(path)
				#showitem.AddAlternativePath("XML Source", "http://" + self.dbconf['DBHostName'] + ":6544/Myth/GetRecording?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", "%20"), )

			self.log("def(LoadShowRecordings): Thumbnail: " + showitem.GetThumbnail())
			self.log("def(LoadShowRecordings): Path: " + showitem.GetPath())

			showitems.append(showitem)

		mc.GetWindow(14002).GetList(2040).SetItems(showitems)

		self.config.Reset("loading")
		self.log("def(LoadShowRecordings): End ===========================================================")


class MythBoxeeMain(MythBoxeeBase):
	"""
	__init__ - Lets make a connection to the backend!
	"""
	def __init__(self):
		MythBoxeeBase.__init__(self)
		
		self.MythBoxeeRecordings = MythBoxeeRecordings()
		self.MythBoxeeRecordings.start()

		self.MythBoxeeMainUIUpdater = MythBoxeeMainUIUpdater()
		self.MythBoxeeMainUIUpdater.start()

	def unload(self):
		self.MythBoxeeRecordings.stop()
		self.MythBoxeeMainUIUpdater.stop()


	"""
	DisplayShow
	
	TODO: rewrite this entire function
	"""
	def DisplayShow(self):
		self.log("def(DisplaySingleShow): Start =========================================================")

		recordingList = mc.GetWindow(14001).GetList(1030)
		itemId = recordingList.GetFocusedItem()
		item = recordingList.GetItem(itemId)
		title = item.GetLabel()

		# Save the Latest Show Title to what was clicked
		# this way the show window has a way to load the data.
		self.config.SetValue("CurrentShowItemID", str(itemId))
		self.config.SetValue("CurrentShowTitle", title)
		self.config.SetValue("CurrentShowID", item.GetProperty("seriesid"))

		self.config.SetValue("cache.changed", "true")

		# Show the Single Show Window
		mc.ActivateWindow(14002)
		self.log("def(DisplaySingleShow): End ===========================================================")


class MythBoxeeShow(MythBoxeeBase):
	def __init__(self):
		MythBoxeeBase.__init__(self)
		self.log("def(LoadShow): Start =========================================================")
		self.config.SetValue("loading", "true")

		self.MythBoxeeRecordings = MythBoxeeRecordings()
		self.MythBoxeeRecordings.start()

		self.MythBoxeeShowUIUpdater = MythBoxeeShowUIUpdater()
		self.MythBoxeeShowUIUpdater.start()

		## Get Current Show Information
		title = self.config.GetValue("CurrentShowTitle")
		seriesid = self.config.GetValue("CurrentShowID")

		self.log("def(LoadSingleShow): Title[" + title + "]")

		## Setup the Show Window and Populate the Window's Lists
		self.SetSortableOptions()
		self.SetSeriesDetails(title, seriesid)
		#self.LoadShowRecordings(title)
		
		self.config.Reset("loading")
		self.log("def(LoadShow): End ===========================================================")


	def unload(self):
		self.MythBoxeeRecordings.stop()
		self.MythBoxeeShowUIUpdater.stop()

	"""
	LoadShowRecordings
	
	Determine which show is being displayed and find all the recordings for it.
	Then populate the recording list for the singular show for viewer to watch.
	"""
	def LoadShowRecordings(self, title):
		self.log("def(LoadShowRecordings): Start =========================================================")

		## Get current sort and filter settings
		sortBy = self.config.GetValue("SortBy")
		sortDir = self.config.GetValue("SortDir")
		theFilter = self.config.GetValue("Filter")

		self.log("def(LoadShowRecordings): Sort By:  " + sortBy)
		self.log("def(LoadShowRecordings): Sort Dir: " + sortDir)
		self.log("def(LoadShowRecordings): Filter:   " + theFilter)

		## Clear the episodes container
		episodes = None

		## Sort based on Sorting Criteria
		if sortBy == "Original Air Date" and sortDir == "Ascending":
			episodes = sorted(self.shows[title], key=itemgetter(4))
		elif sortBy == "Original Air Date" and sortDir == "Descending":
			episodes = sorted(self.shows[title], key=itemgetter(4), reverse=True)
		elif sortBy == "Recorded Date" and sortDir == "Ascending":
			episodes = sorted(self.shows[title], key=itemgetter(5))
		elif sortBy == "Recorded Date" and sortDir == "Descending":
			episodes = sorted(self.shows[title], key=itemgetter(5), reverse=True)
		elif sortBy == "Title" and sortDir == "Ascending":
			episodes = sorted(self.shows[title], key=itemgetter(1))
		elif sortBy == "Title" and sortDir == "Descending":
			episodes = sorted(self.shows[title], key=itemgetter(1), reverse=True)
		else:
			episodes = self.shows[title]

		## Loop through all our recordings, and add them to the list.
		showitems = mc.ListItems()
		for title,subtitle,desc,chanid,airdate,starttime,endtime,watched,ref in episodes:
			#recording = self.recs[ref]

			# Filter the Episodes
			if theFilter == "Watched" and watched == 0:
				continue
			elif theFilter == "Unwatched" and watched == 1:
				continue

			# Create the Item list and populate it
			showitem = mc.ListItem( mc.ListItem.MEDIA_VIDEO_EPISODE )
			showitem.SetLabel(subtitle)
			showitem.SetTitle(subtitle)
			showitem.SetTVShowTitle(title)
			showitem.SetDescription(desc)
			showitem.SetProperty("starttime", starttime)
			#showitem.SetProperty("ref", ref)

			## Sometimes dates aren't set, so generate one if not.
			try:
				date = airdate.split("-")
				showitem.SetDate(int(date[0]), int(date[1]), int(date[2]))
			except:
				showitem.SetDate(2010, 01, 01)


			# Determine Stream Method, Generate Proper Path
			streamMethod = self.config.GetValue("StreamMethod")
			if streamMethod == "XML":
				time = starttime.replace("T", "%20")
				path = "http://" + self.dbconf['DBHostName'] + ":6544/Myth/GetRecording?ChanId=" + chanid + "&StartTime=" + time
				showitem.SetThumbnail("http://" + self.dbconf['DBHostName'] + ":6544/Myth/GetPreviewImage?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", " "))
				showitem.SetPath(path)
			elif streamMethod == "SMB":
				time = starttime.replace("T", "").replace("-", "").replace(":", "").replace(" ","")
				path = "smb://" + self.config.GetValue("smb.username") + ":" + self.config.GetValue("smb.password") + "@" + self.dbconf["DBHostName"] + "/" + self.config.GetValue("smb.share") + "/" + chanid + "_" + time + ".mpg"
				showitem.SetThumbnail(path + ".png")
				showitem.SetPath(path)
				#showitem.AddAlternativePath("XML Source", "http://" + self.dbconf['DBHostName'] + ":6544/Myth/GetRecording?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", "%20"), )

			self.log("def(LoadShowRecordings): Thumbnail: " + showitem.GetThumbnail())
			self.log("def(LoadShowRecordings): Path: " + showitem.GetPath())
			
			showitems.append(showitem)
		
		mc.GetWindow(14002).GetList(2040).SetItems(showitems)
		
		self.log("def(LoadShowRecordings): End ===========================================================")
		

	"""
	SetSortableOptions - Setup the show options; sort by, sort direction, watched vs unwatched
	"""
	def SetSortableOptions(self):
		self.log("def(SetSortableOptions): Start =========================================================")

		## Setup Sortable Field Options
		sortable = ['Original Air Date', 'Recorded Date', 'Title']
		items = mc.ListItems()
		for sorttype in sortable:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(sorttype)
			items.append(item)
		mc.GetWindow(14002).GetList(2051).SetItems(mc.ListItems())
		mc.GetWindow(14002).GetList(2051).SetItems(items)

		## Setup Sortable Direction Options
		sortableby = ['Ascending', 'Descending']	
		items = mc.ListItems()
		for sorttype in sortableby:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(sorttype)
			items.append(item)
		mc.GetWindow(14002).GetList(2061).SetItems(mc.ListItems())
		mc.GetWindow(14002).GetList(2061).SetItems(items)

		## Setup Filter Options
		filters = ['All', 'Watched', 'Unwatched']
		items = mc.ListItems()
		for single_filter in filters:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(single_filter)
			items.append(item)
		mc.GetWindow(14002).GetList(2082).SetItems(mc.ListItems())
		mc.GetWindow(14002).GetList(2082).SetItems(items)

		## Set the currently selected option in each category
		mc.GetWindow(14002).GetList(2051).SetSelected(sortable.index(self.config.GetValue("SortBy")), True)
		mc.GetWindow(14002).GetList(2061).SetSelected(sortableby.index(self.config.GetValue("SortDir")), True)
		mc.GetWindow(14002).GetList(2082).SetSelected(filters.index(self.config.GetValue("Filter")), True)
		
		self.log("def(SetSortableOptions): End ===========================================================")


	"""
	SetSeriesDetails - Get Show Series Information
	
	TODO -- rewrite this entire function
	"""
	def SetSeriesDetails(self, title, seriesid):
		self.log("def(SetSeriesDetails): Start =========================================================")

		t = tvdb_api.Tvdb(apikey=self.tvdb_apikey)
		s = t[title.encode('utf-8')]

		overview = s['overview'].encode('utf-8')
		poster = str(s['poster'])

		items = mc.ListItems()
		item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
		item.SetLabel(title)
		item.SetTitle(title)

		self.log("Overview: " + overview)
		self.log("Poster: " + poster)

		try:
			item.SetDescription(overview)
			item.SetProperty("description", overview)
		except:
			item.SetDescription("No Description")
			item.SetProperty("description", "No Description")
		
		try:
			item.SetThumbnail(poster)
		except:
			item.SetThumbnail("mb_poster_error.png")

		items.append(item)

		mc.GetWindow(14002).GetList(2070).SetItems(items)
		self.log("def(SetSeriesDetails): End ===========================================================")


	"""
	FilterEpisodes - Filter the list of Episodes (All, Watched, Unwatched)
	"""
	def FilterEpisodes(self):
		self.log("def(FilterEpisodes): Start =========================================================")

		## Figure out how we need to filter
		FilterItems = FilterItemNumber = mc.GetWindow(14002).GetList(2082).GetSelected()
		mc.GetWindow(14002).GetList(2082).UnselectAll()
		mc.GetWindow(14002).GetList(2082).SetSelected(mc.GetWindow(14002).GetList(2082).GetFocusedItem(), True)

		## Update the Filter Criteria
		self.config.SetValue("Filter", mc.GetWindow(14002).GetList(2082).GetItem(mc.GetWindow(14002).GetList(2082).GetFocusedItem()).GetLabel())

		## Now that the filter has changed, reload the list of episodes
		self.LoadShowRecordings(self.config.GetValue("CurrentShowTitle"))
		self.log("def(FilterEpisodes): End ===========================================================")


	"""
	SortBy - Set the Field that the List of Episodes is Sorted By
	"""
	def SortBy(self):
		self.log("def(SortBy): Start =========================================================")

		## Figure out how we need to Sort
		sortByItems = sortByItemNumber = mc.GetWindow(14002).GetList(2051).GetSelected()
		mc.GetWindow(14002).GetList(2051).UnselectAll()
		mc.GetWindow(14002).GetList(2051).SetSelected(mc.GetWindow(14002).GetList(2051).GetFocusedItem(), True)

		## Update the Sort Criteria
		self.config.SetValue("SortBy", mc.GetWindow(14002).GetList(2051).GetItem(mc.GetWindow(14002).GetList(2051).GetFocusedItem()).GetLabel())

		self.log("def(SortBy): Direction: " + self.config.GetValue("SortBy"))

		## Now that we have updated the Sort Criteria, reload the shows
		self.LoadShowRecordings(self.config.GetValue("CurrentShowTitle"))
		self.log("def(SortBy): End ===========================================================")

	"""
	SortDir - Set the Direction that the List of Episodes is Sorted By
	"""
	def SortDir(self):
		self.log("def(SortDir): Start =========================================================")
		
		## Figure out how we need to Sort
		sortDirectionItems = sortDirectionItemNumber = mc.GetWindow(14002).GetList(2061).GetSelected()
		mc.GetWindow(14002).GetList(2061).UnselectAll()
		mc.GetWindow(14002).GetList(2061).SetSelected(mc.GetWindow(14002).GetList(2061).GetFocusedItem(), True)

		## Update the Sort Criteria
		self.config.SetValue("SortDir", mc.GetWindow(14002).GetList(2061).GetItem(mc.GetWindow(14002).GetList(2061).GetFocusedItem()).GetLabel())

		self.log("def(SortDir): Direction: " + self.config.GetValue("SortDir"))

		## Now that we have updated the Sort Criteria, reload the shows
		self.LoadShowRecordings(self.config.GetValue("CurrentShowTitle"))
		self.log("def(SortDir): End =========================================================")


class MythBoxeeStatus(MythBoxeeBase):

	def __init__(self):
		MythBoxeeBase.__init__(self)

		self.log("def(StatusInit): Start =========================================================")
		self.config.SetValue("loadingstatus", "true")

		# Set the version on any page that loads
		mc.GetActiveWindow().GetLabel(1013).SetLabel(self.version)

		# Grab data from the backend for status screen
		try:
			uptime = self.be.getUptime()
			load = self.be.getLoad()
			freespace = self.be.getFreeSpace()
			guidedata = self.be.getLastGuideData()
			isRecording = self.be.isRecording(1)
			freespacesummary = self.be.getFreeSpaceSummary()
			recorders = self.be.getRecorderList()
			upcoming = self.be.getUpcomingRecordings()
		except Exception, e:
			self.log("def(StatusInit): Exception: " + str(sys.exc_info()[0]))
			mc.ShowDialogOk("MythBoxee", "Whoops! Something went wrong while trying to load this screen. Try again.")
			self.config.Reset("loadingstatus")
			mc.CloseWindow()

		# Setup storage information for status screen
		free_txt = "Storage:\n"
		for free in freespace:
			free_txt = free_txt + "  " + str(free.path) + " (" + "Total: " + str(free.totalspace) + ", Free: " + str(free.freespace) + ", Used: " + str(free.usedspace) + ")\n"
		guide_txt = "There is guide data until " + str(guidedata) + ".\n"
		load_txt = "Load: " + str(load)
		uptime_txt = "Uptime: " + str(uptime)
		sys_info = load_txt + "\n\n" + uptime_txt + "\n\n" + free_txt + "\n" + guide_txt

		if isRecording == True:
			try:
				currentRecording = self.be.getCurrentRecording(1)
			except Exception, e:
				self.log("def(StatusInit): Failed to get Current Recording Information")

			is_recording_txt = "is recording on channel " + str(currentRecording.callsign) + " (" + str(currentRecording.channum) + ")"

			itemList = mc.ListItems()
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetThumbnail(self.banners[str(currentRecording.title)])
			itemList.append(item)
			mc.GetWindow(14003).GetList(1025).SetItems(itemList)
			mc.GetWindow(14003).GetLabel(1026).SetLabel(str(currentRecording.title) + ": " + str(currentRecording.subtitle))
		else:
			is_recording_txt = "is not recording"

		# Set encoder information up
		mc.GetWindow(14003).GetLabel(1023).SetLabel("Encoder " + str(recorders[0]) + " " + is_recording_txt + ".")
		mc.GetWindow(14003).GetLabel(1033).SetLabel(sys_info)

		self.log("def(StatusInit): Recorders: " + str(recorders))
		self.log("def(StatusInit): Uptime: " + str(uptime))
		self.log("def(StatusInit): Load: " + str(load))
		self.log("def(StatusInit): Free Space: " + str(freespace))
		self.log("def(StatusInit): Guide Data: " + str(guidedata))
		self.log("def(StatusInit): Summary: " + str(freespacesummary))
		self.log("def(StatusInit): Upcoming: " + str(upcoming))
		self.log("def(StatusInit): Recording: " + str(isRecording))

		self.config.Reset("loadingstatus")
		self.log("def(StatusInit): End ===========================================================")
		


class MythBoxeeSettings(MythBoxeeBase):
	def __init__(self):
		MythBoxeeBase.__init__(self)
		
		self.log("def(SettingsInit): Start =========================================================")
		self.config.SetValue("loadingsettings", "true")

		# Set the version on any page that loads
		mc.GetActiveWindow().GetLabel(1013).SetLabel(self.version)

		if not self.config.GetValue("dbconn"):
			mc.ShowDialogOk("MythBoxee", "Welcome to MythBoxee! Looks like this is the first time you have run this app. Please fill out all the settings and you'll be on your way to using this app.")
			response = mc.ShowDialogConfirm("MythBoxee", "Do you know what your Security Pin is for your MythTV Backend? If not, we'll try the default, if that fails, you'll need to fill your database information in manually.", "No", "Yes")
			if response:
				pin = mc.ShowDialogKeyboard("Security Pin", "", True)
				self.config.SetValue("pin", str(pin))
			else:
				pin = 0000
				self.config.SetValue("pin", str(pin))

			mc.GetWindow(14004).GetLabel(9002).SetLabel("Attempting Database Connection ...")
			if self.DiscoverBackend() == False:
				mc.ShowDialogOk("MythBoxee", "Unfortunately MythBoxee wasn't able to auto-discover your MythTV backend and database credentials. Please enter them in manually.")
				mc.GetWindow(14004).GetLabel(9002).SetLabel("LOADING...")
				self.LoadSettings()
			else:
				mc.ShowDialogOk("MythBoxee", "MythBoxee auto-discovered your MythTV backend. Enjoy your recordings!")
				self.config.Reset("app.lastruntime")
				mc.CloseWindow()
		else:
			self.LoadSettings()
		self.config.Reset("loadingsettings")
		self.log("def(SettingsInit): End ===========================================================")

	"""
	LoadSettings - Stuff that needs to be executed when settings window is loaded
	"""
	def LoadSettings(self):
		self.log("def(LoadSettings): Start =========================================================")

		## Grab the current StreamMethod
		streamMethod = self.config.GetValue("StreamMethod")

		self.log("def(LoadSettings): Stream Method: " + streamMethod)

		# Grab and Set the Database Information
		if self.config.GetValue("dbconn"):
			dbconf = eval(self.config.GetValue("dbconn"))
			mc.GetWindow(14004).GetEdit(1042).SetText(dbconf['DBHostName'])
			mc.GetWindow(14004).GetEdit(1043).SetText(dbconf['DBUserName'])
			mc.GetWindow(14004).GetEdit(1044).SetText(dbconf['DBPassword'])
			mc.GetWindow(14004).GetEdit(1045).SetText(dbconf['DBName'])
			mc.GetWindow(14004).GetControl(1032).SetFocus()
		else:
			mc.GetWindow(14004).GetControl(1042).SetFocus()

		# Setup Stream Methods for user to choose
		methods = ['XML', 'SMB']
		items = mc.ListItems()
		for method in methods:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(method)
			items.append(item)
		mc.GetWindow(14004).GetList(1022).SetItems(items)
		mc.GetWindow(14004).GetList(1022).SetSelected(methods.index(streamMethod), True)

		# Depending on StreamMethod Enable Options
		if not streamMethod or streamMethod == "XML":
			mc.GetWindow(14004).GetControl(1032).SetEnabled(False)
			mc.GetWindow(14004).GetControl(1033).SetEnabled(False)
			mc.GetWindow(14004).GetControl(1034).SetEnabled(False)
		else:
			if not self.config.GetValue("smb.username"):
				self.config.SetValue("smb.username", "guest")
			if not self.config.GetValue("smb.password"):
				self.config.SetValue("smb.password", "guest")

			self.log("def(LoadSettings): smb.share: " + self.config.GetValue("smb.share"))
			self.log("def(LoadSettings): smb.username: " + self.config.GetValue("smb.username"))
			self.log("def(LoadSettings): smb.password: " + self.config.GetValue("smb.password"))

			## Since the Stream Method is SMB enable controls for setting info
			mc.GetWindow(14004).GetControl(1032).SetEnabled(True)
			mc.GetWindow(14004).GetControl(1033).SetEnabled(True)
			mc.GetWindow(14004).GetControl(1034).SetEnabled(True)

			## Update the fields with current SMB settings.
			mc.GetWindow(14004).GetEdit(1032).SetText(self.config.GetValue("smb.share"))
			mc.GetWindow(14004).GetEdit(1033).SetText(self.config.GetValue("smb.username"))
			mc.GetWindow(14004).GetEdit(1034).SetText(self.config.GetValue("smb.password"))

		self.log("def(LoadSettings): End ===========================================================")


	"""
	SetStreamMethod - Change the Streaming Method
	"""
	def SetStreamMethod(self):
		self.log("def(SetStreamMethod): Start =========================================================")

		## Figure out what Stream Method the user has selected
		streamMethodItems = streamMethodItemNumber = mc.GetWindow(14004).GetList(1022).GetSelected()
		mc.GetWindow(14004).GetList(1022).UnselectAll()
		mc.GetWindow(14004).GetList(1022).SetSelected(mc.GetWindow(14004).GetList(1022).GetFocusedItem(), True)
		streamMethod = mc.GetWindow(14004).GetList(1022).GetItem(mc.GetWindow(14004).GetList(1022).GetFocusedItem()).GetLabel()

		## Disabled some UI pieces depending on stream method
		if not streamMethod or streamMethod == "XML":
			mc.GetWindow(14004).GetControl(1032).SetEnabled(False)
			mc.GetWindow(14004).GetControl(1033).SetEnabled(False)
			mc.GetWindow(14004).GetControl(1034).SetEnabled(False)
		else:
			mc.GetWindow(14004).GetControl(1032).SetEnabled(True)
			mc.GetWindow(14004).GetControl(1033).SetEnabled(True)
			mc.GetWindow(14004).GetControl(1034).SetEnabled(True)

		## Save the Stream Method
		self.config.SetValue("StreamMethod", streamMethod)

		## Notify the User
		mc.ShowDialogNotification("Stream Method Changed to " + streamMethod)

		self.log("def(SetStreamMethod): Stream Method Changed to -- " + streamMethod)
		self.log("def(SetStreamMethod): End =========================================================")


	"""
	SaveDbSettings - Save Database Settings
	"""
	def SaveDbSettings(self):
		self.log("def(SaveDbSettings): Start =========================================================")

		dbconf = {}
		dbconf['DBHostName'] = mc.GetWindow(14004).GetEdit(1042).GetText()
		dbconf['DBUserName'] = mc.GetWindow(14004).GetEdit(1043).GetText()
		dbconf['DBPassword'] = mc.GetWindow(14004).GetEdit(1044).GetText()
		dbconf['DBName'] = mc.GetWindow(14004).GetEdit(1045).GetText()

		self.config.SetValue("dbconn", str(dbconf))

		## Notify the user that the changes have been saved.
		mc.ShowDialogNotification("Database Settings Saved")

		self.log("def(SaveDbSettings): End ===========================================================")


	"""
	TestDbSettings - Test Database Settings
	"""
	def TestDbSettings(self):
		self.log("def(TestDbSettings): Start =========================================================")
		self.config.SetValue("loadingsettings", "true")
		mc.GetWindow(14004).GetLabel(9002).SetLabel("Attempting Database Connection ...")

		dbconf = {}
		dbconf['DBHostName'] = mc.GetWindow(14004).GetEdit(1042).GetText()
		dbconf['DBUserName'] = mc.GetWindow(14004).GetEdit(1043).GetText()
		dbconf['DBPassword'] = mc.GetWindow(14004).GetEdit(1044).GetText()
		dbconf['DBName'] = mc.GetWindow(14004).GetEdit(1045).GetText()

		try:
			self.log("def(TestDbSettings): Attempting Database Connection ...")
			mythtv.MythDB(**dbconf)
		except MythError, e:
			self.log("def(TestDbSettings): Error: " + e.message)
			mc.ShowDialogNotification("Failed to connect to the MythTV Backend")
		else:
			self.SaveDbSettings()
			mc.ShowDialogNotification("Connection to MythTV Backend Success. Settings Saved.")

		self.config.Reset("loadingsettings")
		self.log("def(TestDbSettings): End ===========================================================")


	"""
	SaveSMBSettings - Saves the SMB settings the user inputted.
	"""
	def SaveSMBSettings(self):
		self.log("def(SetStreamMethod): Start =========================================================")

		## Save SMB settings the user inputted
		self.config.SetValue("smb.share", mc.GetWindow(14004).GetEdit(1032).GetText())
		self.config.SetValue("smb.username", mc.GetWindow(14004).GetEdit(1033).GetText())
		self.config.SetValue("smb.password", mc.GetWindow(14004).GetEdit(1034).GetText())

		## Notify the user that the changes have been saved.
		mc.ShowDialogNotification("SMB Share Settings Saved")

		self.log("def(SetStreamMethod): End ===========================================================")
