import mc
import re
import sys
import random
import time
import pickle
import mythtv
from mythtv import MythError
from operator import itemgetter, attrgetter


class MythBoxee:
	logLevel = 1
	version = "4.23.3.beta"
	userAgent = "MythBoxee v4.32.3.beta"
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
	__init__ - Lets make a connection to the backend!
	"""
	def __init__(self):
		self.log("def(__init__): Start =========================================================")
		self.log("def(__init__): Version: " + self.version)
		self.log("def(__init__): Python Version: " + str(sys.version_info))

		self.config = mc.GetApp().GetLocalConfig()

		# We'll use this to determine when to reload data.
		self.config.SetValue("LastRunTime", str(time.time()))
		self.config.SetValue("CurrentShowItemID", "0")

		# If this is the first time the app is being run, lets set some default options.
		if not self.config.GetValue("app.firstrun"):
			self.config.SetValue("SortBy", "Original Air Date")
			self.config.SetValue("SortDir", "Descending")
			self.config.SetValue("Filter", "All")
			self.config.SetValue("StreamMethod", "XML")
			self.config.SetValue("app.firstrun", "true")


		# If dbconn isn't set, we'll assume we haven't found the backend.
		if not self.config.GetValue("dbconn"):
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
				self.GetRecordings()

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
	LoadMain - Loader for Main Window
	"""
	def LoadMain(self):
		self.log("def(LoadMain): Start =========================================================")
		self.config.SetValue("loadingmain", "true")
		
		if not self.config.GetValue("dbconn"):
			return False

		## Put focus on last selected item
		itemId = int(self.config.GetValue("CurrentShowItemID"))
		if itemId and itemId != 0:
			mc.GetWindow(14001).GetList(1030).SetFocusedItem(itemId)

		cacheTime = self.config.GetValue("cache.time")
		mainItems = len(mc.GetWindow(14001).GetList(1030).GetItems())

		if not cacheTime or mainItems == 0 or cacheTime <= str(time.time() - 2400):
			self.SetShows()
			
		self.config.Reset("loadingmain")
		self.log("def(LoadMain): End ===========================================================")


	"""
	RefreshMain - Refresh the Main Window
	"""
	def RefreshMain(self):
		self.log("def(RefreshMain): Start =========================================================")
		self.config.SetValue("loadingmain", "true")
		
		self.config.Reset("cache.time")
		self.GetRecordings()
		self.SetShows()

		self.config.Reset("loadingmain")
		self.log("def(RefreshMain): End ===========================================================")


	"""
	GetRecordings - Pulls all of the recordings out of the backend and prepares them for use in the app.
	
	This function also creates some dictionarys and lists of information
	that is used throughout the app for different functions.
	"""
	def GetRecordings(self):
		self.log("def(GetRecordings): Start =========================================================")
		self.config.SetValue("loadingmain", "true")

		# Empty out crucial info
		self.titles = []
		self.banners = {}
		self.series = {}
		self.shows = {}

		cacheTime = self.config.GetValue("cache.time")
		mainItems = len(mc.GetWindow(14001).GetList(1030).GetItems())

		self.recs = self.be.getRecordings()
		
		if not cacheTime or mainItems == 0 or cacheTime <= str(time.time() - 2400):
			x=0
			for recording in self.recs:
				if recording.title not in self.titles:
					self.titles.append(str(recording.title))
					self.banners[str(recording.title)] = self.GetRecordingArtwork(str(recording.title))
					self.series[str(recording.title)] = self.GetRecordingSeriesID(str(recording.title))
					self.shows[str(recording.title)] = []

				if recording.subtitle == None:
					subtitle = ""
				else:
					subtitle = recording.subtitle.encode('utf-8')

				single = [recording.title.encode('utf-8'), subtitle, str(recording.description), str(recording.chanid), str(recording.airdate), str(recording.starttime), str(recording.endtime), recording.getRecorded().watched, x]
				self.shows[str(recording.title)].append(single)
				x = x + 1

				# Lets cache our findings for now.
				self.config.SetValue("cache.time", str(time.time()))
				self.config.SetValue("cache.titles", pickle.dumps(self.titles))
				self.config.SetValue("cache.banners", pickle.dumps(self.banners))
				self.config.SetValue("cache.series", pickle.dumps(self.series))
				self.config.SetValue("cache.shows", pickle.dumps(self.shows))
		else:
			self.titles = pickle.loads(self.config.GetValue("cache.titles"))
			self.banners = pickle.loads(self.config.GetValue("cache.banners"))
			self.series = pickle.loads(self.config.GetValue("cache.series"))
			self.shows = pickle.loads(self.config.GetValue("cache.shows"))

		self.titles.sort()

		self.config.Reset("loadingmain")
		self.log("def(GetRecordings): End ===========================================================")
		

	"""
	SetShows - Populate the Shows List on the Main Window
	"""
	def SetShows(self):
		self.log("def(SetShows): Start =========================================================")
		items = mc.ListItems()
		for title in self.titles:
			item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
			item.SetLabel(str(title))
			item.SetThumbnail(self.banners[title])
			item.SetProperty("videos", str(len(self.shows[title])))
			item.SetProperty("seriesid", str(self.series[title]))
			items.append(item)
		mc.GetWindow(14001).GetList(1030).SetItems(items)
		self.log("def(SetShows): End ===========================================================")
		

	"""
	GetRecordingArtwork - Get the Artwork for a show.
	"""
	def GetRecordingArtwork(self, title):
		self.log("def(GetRecordingArtwork): Start =========================================================")

		sg = mc.Http()
		sg.SetUserAgent(self.userAgent)
		html = sg.Get("http://www.thetvdb.com/api/GetSeries.php?seriesname=" + str(title.replace(" ", "%20")))
		banners = re.compile("<banner>(.*?)</banner>").findall(html)

		## Sometimes we can't find the show, so we have to provide our own artwork
		try:
			artwork = "http://www.thetvdb.com/banners/" + banners[0]
		except:
			artwork = "mb_artwork_error.png"

		self.log("def(GetRecordingArtwork): URL: " + str(artwork))
		self.log("def(GetRecordingArtwork): End =========================================================")

		return artwork


	"""
	GetRecordingSeriesID - Get the Series ID of a show.
	
	TODO: rewrite this entire function
	"""
	def GetRecordingSeriesID(self, title):
		self.log("def(GetRecordingSeriesID): Start =========================================================")
		sg = mc.Http()
		sg.SetUserAgent(self.userAgent)
		html = sg.Get("http://www.thetvdb.com/api/GetSeries.php?seriesname=" + title.replace(" ", "%20"))
		series = re.compile("<seriesid>(.*?)</seriesid>").findall(html)

		## Sometimes we can't determine the series ID
		try:
			seriesid = series[0]
		except:
			seriesid = 00000

		self.log("def(GetRecordingSeriesID): Title:    " + title)
		self.log("def(GetRecordingSeriesID): SeriesID: " + str(seriesid))
		self.log("def(GetRecordingSeriesID): End ===========================================================")
		return seriesid


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

		# Show the Single Show Window
		mc.ActivateWindow(14002)
		
		itemList = mc.ListItems()
		itemList.append(item)
		
		mc.GetWindow(14002).GetList(2070).SetItems(itemList)

		self.log("def(DisplaySingleShow): Title[" + title + "]")		
		self.log("def(DisplaySingleShow): Current Show Title:     " + title)
		self.log("def(DisplaySingleShow): Current Show Item ID:   " + str(itemId))
		self.log("def(DisplaySingleShow): Current Show Series ID: " + item.GetProperty("seriesid"))
		self.log("def(DisplaySingleShow): End ===========================================================")


	"""
	LoadShow - init function for Show Window
	"""
	def LoadShow(self):
		self.log("def(LoadShow): Start =========================================================")
		self.config.SetValue("loading", "true")

		## Get Current Show Information
		title = self.config.GetValue("CurrentShowTitle")
		seriesid = self.config.GetValue("CurrentShowID")

		self.log("def(LoadSingleShow): Title[" + title + "]")

		## Setup the Show Window and Populate the Window's Lists
		self.SetSortableOptions()
		self.SetSeriesDetails(title, seriesid)
		self.LoadShowRecordings(title)
		
		self.config.Reset("loading")
		self.log("def(LoadShow): End ===========================================================")


	"""
	LoadShowRecordings
	
	Determine which show is being displayed and find all the recordings for it.
	Then populate the recording list for the singular show for viewer to watch.
	"""
	def LoadShowRecordings(self, title):
		self.log("def(LoadShowRecordings): Start =========================================================")

		dbconf = eval(self.config.GetValue("dbconn"))

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
				showitem.SetThumbnail("http://" + self.dbconf['DBHostName'] + ":6544/Myth/GetPreviewImage?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", "%20"))
				showitem.SetPath(path)
			elif streamMethod == "SMB":
				time = starttime.replace("T", "").replace("-", "").replace(":", "").replace(" ","")
				path = "smb://" + self.config.GetValue("smb.username") + ":" + self.config.GetValue("smb.password") + "@" + self.dbconf["DBHostName"] + "/" + self.config.GetValue("smb.share") + "/" + chanid + "_" + time + ".mpg"
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


	"""
	SettingsInit - Init function for Settings Window
	"""
	def SettingsInit(self):
		self.config.SetValue("loadingsettings", "true")
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
