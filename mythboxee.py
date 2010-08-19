import mc
import re
import mythtv
from mythtv import MythError
from operator import itemgetter, attrgetter


class MythBoxee:
	logLevel = 1
	version = "4.0.beta"

	userAgent = "MythBoxee v4.0.beta"
	tvdb_apikey = "6BEAB4CB5157AAE0"

	be = None
	db = None

	recs = None
	titles = []
	recordings = []
	banners = {}
	shows = {}
	series = {}


	"""
	DiscoverBackend - just as it sounds
	
	Attempt to discover the MythTV Backend using UPNP protocol, once found
	try and gather MySQL database connection information using default PIN
	via the XML interface. If that fails then prompt user to enter their
	custom SecurityPin, if we fail to gather database information that way
	finally prompt user to enter their credentials manually.
	"""
	def DiscoverBackend():
		self.log("def(DiscoverBackend)")

		pin = self.config.GetValue("pin")
		dbconn = self.config.GetValue("dbconn")

		if not pin:
			pin = 0000

		try:
			self.db = mythtv.MythDB(SecurityPin=pin)
		except Exception, e:
			if e.ename == 'DB_CREDENTIALS' and count < 2:
				mc.ActivateWindow(14002)
				mc.GetWindow(14002).GetControl(6020).SetVisible(False)
				mc.GetWindow(14002).GetControl(6010).SetVisible(True)
				mc.GetWindow(14002).GetControl(6011).SetFocus()
			elif e.ename == 'DB_CONNECTION' or e.ename == 'DB_CREDENTIALS' and count > 3:
				mc.ActivateWindow(14002)
				mc.GetWindow(14002).GetControl(6010).SetVisible(False)
				mc.GetWindow(14002).GetControl(6020).SetVisible(True)
				mc.GetWindow(14002).GetControl(6021).SetFocus()
			return False
		else:
			self.config.SetValue("dbconn", str(self.db.dbconn))
			return True


	"""
	Lets make a connection to the backend!
	"""
	def __init__(self):
		self.config = mc.GetApp().GetLocalConfig()

		self.log("def(__init__)")

		# If this is the first time the app is being run, lets set some default options.
		if not self.config.GetValue("firstrun"):
			self.config.SetValue("SortBy", "Original Air Date")
			self.config.SetValue("SortDir", "Descending")
			self.config.SetValue("firstrun", "1")

		# If dbconn isn't set, we'll assume we haven't found the backend.
		if not self.config.GetValue("dbconn"):
			discoverBackend = False
			while discoverBackend is False:
				print "discover"
				discoverBackend = self.DiscoverBackend()

		# Parse our DB info
		dbconn = self.config.GetValue("dbconn")
		dbconf = eval(dbconn)

		# Now that the backend has been discovered, lets connect.
		try:
			self.db = mythtv.MythDB(**dbconf)
		except MythError, e:
			print e.message
			mc.ShowDialogNotification("Failed to connect to the MythTV Backend")
		else:
			self.be = mythtv.MythBE(db=self.db)

	"""
	GetRecordings - Pulls all of the recordings out of the backend.
	
	This function also creates some dictionarys and lists of information
	that is used throughout the app for different functions.
	"""
	def GetRecordings(self):
		self.titles = []
		self.banners = {}
		self.series = {}
		self.shows = {}

		self.log("def(GetRecordings)")

		self.recs = self.be.getRecordings()
		
		x=0
		for recording in self.recs:
			if recording.title not in self.titles:
				self.titles.append(str(recording.title))
				self.banners[str(recording.title)] = self.GetRecordingArtwork(str(recording.title))
				self.series[str(recording.title)] = self.GetRecordingSeriesID(str(recording.title))
				self.shows[str(recording.title)] = []
			
			single = [str(recording.title), str(recording.subtitle), str(recording.description), str(recording.chanid), str(recording.airdate), str(recording.starttime), str(recording.endtime), x]
			self.shows[str(recording.title)].append(single)
			x = x + 1
		
		self.titles.sort()

		items = mc.ListItems()
		for title in self.titles:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(str(title))
			item.SetThumbnail(self.banners[title])
			item.SetProperty("videos", str(len(self.shows[title])))
			item.SetProperty("seriesid", str(self.series[title]))
			items.append(item)

		mc.GetWindow(14001).GetList(1030).SetItems(items)


	def GetRecordingArtwork(self, title):
		sg = mc.Http()
		sg.SetUserAgent('MythBoxee v4.0.beta')
		html = sg.Get("http://www.thetvdb.com/api/GetSeries.php?seriesname=" + str(title.replace(" ", "%20")))
		banners = re.compile("<banner>(.*?)</banner>").findall(html)

		try:
			artwork = "http://www.thetvdb.com/banners/" + banners[0]
		except:
			artwork = "mb_artwork_error.png"

		self.log("def(GetRecordingArtwork): " + str(artwork))

		return artwork

	def GetRecordingSeriesID(self, title):
		sg = mc.Http()
		sg.SetUserAgent(self.userAgent)
		html = sg.Get("http://www.thetvdb.com/api/GetSeries.php?seriesname=" + title.replace(" ", "%20"))
		series = re.compile("<seriesid>(.*?)</seriesid>").findall(html)

		try:
			seriesid = series[0]
		except:
			seriesid = 00000

		self.log("def(GetRecordingSeriesID): title[" + title + "] - seriesid[" + str(seriesid) + "]")

		return seriesid


	"""
	DisplayShow
	"""
	def DisplayShow(self):
		recordingList = mc.GetWindow(14001).GetList(1030)
		item = recordingList.GetItem(recordingList.GetFocusedItem())
		title = item.GetLabel()

		# Save the Latest Show Title to what was clicked
		# this way the show window has a way to load the data.
		self.config.SetValue("LatestShowTitle", title)
		self.config.SetValue("LatestShowID", item.GetProperty("seriesid"))

		self.log("def(DisplaySingleShow): Title[" + title + "]")
		
		# Show the Single Show Window
		mc.ActivateWindow(14002)
		
		itemList = mc.ListItems()
		itemList.append(item)
		
		mc.GetWindow(14002).GetList(2070).SetItems(itemList)


	"""
	LoadShow
	
	Launch function to gather and setup the recordings for a single show.
	"""
	def LoadShow(self):
		title = self.config.GetValue("LatestShowTitle")
		seriesid = self.config.GetValue("LatestShowID")

		self.log("def(LoadSingleShow): Title[" + title + "]")

		self.SetSortableOptions()
		self.SetSeriesDetails(title, seriesid)
		self.LoadShowRecordings(title)


	"""
	LoadShowRecordings
	
	Determine which show is being displayed and find all the recordings for it.
	Then populate the recording list for the singular show for viewer to watch.
	"""
	def LoadShowRecordings(self, title):
		sortBy = self.config.GetValue("SortBy")
		sortDir = self.config.GetValue("SortDir")

		episodes = None

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

		showitems = mc.ListItems()
		for title,subtitle,desc,chanid,airdate,starttime,endtime,ref in episodes:
			print title
			recording = self.recs[ref]
			#showitem = mc.ListItem( mc.ListItem.MEDIA_VIDEO_EPISODE )
			#showitem = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			showitem = mc.ListItem()
			showitem.SetLabel(str(recording.subtitle))
			showitem.SetTitle(str(recording.subtitle))
			showitem.SetTVShowTitle(str(recording.title))
			showitem.SetDescription(str(desc))
			showitem.SetProperty("starttime", str(starttime))
			showitem.SetProperty("ref", str(ref))

			try:
				date = str(airdate).split("-")
				showitem.SetDate(int(date[0]), int(date[1]), int(date[2]))
			except:
				showitem.SetDate(2010, 01, 01)

			dbconf = eval(self.config.GetValue("dbconn"))

			#showitem.SetThumbnail("http://192.168.1.210:6544/Myth/GetPreviewImage?ChanId=1050&StartTime=2010-08-05%2021:00:00") 
			#showitem.SetThumbnail("http://192.168.1.210:6544/Myth/GetPreviewImage?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", "%20")) 
			showitem.SetThumbnail("http://" + dbconf['DBHostName'] + ":6544/Myth/GetPreviewImage?ChanId=" + chanid + "&StartTime=" + starttime.replace(" ", "%20"))
			
			#showitem.SetPath("http://" + dbconf['DBHostName'] + ":6544/Myth/GetRecording?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", "%20")) 
			showitem.SetPath("smb://guest:guest@192.168.1.210/recordings/1050_20100709010000.mpg")
			
			showitems.append(showitem)
		
		mc.GetWindow(14002).GetList(2040).SetItems(mc.ListItems())
		mc.GetWindow(14002).GetList(2040).SetItems(showitems)
		

	"""
	SetShowOptions
	
	Setup the show options; sort by, sort direction, watched vs unwatched
	"""
	def SetSortableOptions(self):
		sortable = ['Original Air Date', 'Recorded Date', 'Title']
		items = mc.ListItems()
		for sorttype in sortable:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(sorttype)
			items.append(item)

		mc.GetWindow(14002).GetList(2051).SetItems(items)
		mc.GetWindow(14002).GetList(2051).SetSelected(1, True)

		sortableby = ['Ascending', 'Descending']	
		items = mc.ListItems()
		for sorttype in sortableby:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(sorttype)
			items.append(item)

		mc.GetWindow(14002).GetList(2061).SetItems(items)
		mc.GetWindow(14002).GetList(2061).SetSelected(1, True)
		

	def SetSeriesDetails(self, title, seriesid):
		sg = mc.Http()
		sg.SetUserAgent(self.userAgent)
		html = sg.Get("http://thetvdb.com/api/" + self.tvdb_apikey + "/series/" + seriesid + "/")
		overview = re.compile("<Overview>(.*?)</Overview>").findall(html)
		poster = re.compile("<poster>(.*?)</poster>").findall(html)
		items = mc.ListItems()
		item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
		item.SetLabel(title)
		item.SetTitle(title)
		try:
			item.SetDescription(overview[0])
			item.SetProperty("description", overview[0])
		except:
			item.SetDescription("No Description")
			item.SetProperty("description", "No Description")
		
		try:
			item.SetThumbnail("http://www.thetvdb.com/banners/" + poster[0])
		except:
			item.SetThumbnail("mb_poster_error.png")

		items.append(item)

		mc.GetWindow(14002).GetList(2070).SetItems(items)


	def PlayRecording(self):
		self.log("def(PlayRecording): ")
		
		sl = mc.GetWindow(14002).GetList(2040)
		item = sl.GetItem(sl.GetFocusedItem())

		ref = item.GetProperty("ref")
		
		file = self.recs[int(ref)].open('r', self.db)

		mc.ShowDialogNotification(item.GetProperty("ref"))
		mc.ShowDialogNotification("Playing: " + item.GetLabel())


	def log(self, message):
		if self.logLevel >= 2:
			mc.ShowDialogNotification(message)
			
		if self.logLevel >= 1:
			mc.LogInfo(">>> MythBoxee (" + self.version + ")\: " + message)

		print ">>> MythBoxee (" + self.version + ")\: " + message
