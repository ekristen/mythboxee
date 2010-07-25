import mc
import re
from operator import itemgetter, attrgetter
from xml.dom import minidom

config = mc.GetApp().GetLocalConfig()

if not config.GetValue("SortBy"):
	config.SetValue("SortBy", "Original Air Date")
if not config.GetValue("SortDir"):
	config.SetValue("SortDir", "Descending")


titles = []
recordings = []
idbanners = {}
shows = {}
	
def LoadShows():
	del titles[:]
	del recordings[:]
	idbanners.clear()
	shows.clear()

	config = mc.GetApp().GetLocalConfig()

	print "MythBoxee (LoadShows): Accessing MythTV Backend [" + "http://" + config.GetValue("server") + ":6544/Myth/GetRecorded" + "]"

	domXml = minidom.parse("http://" + config.GetValue("server") + ":6544/Myth/GetRecorded")

	programs = domXml.getElementsByTagName("Program")
	channels = domXml.getElementsByTagName("Channel")
	
	x=0
	for dom in programs:
		title = str(dom.getAttribute("title"))
		subtitle = str(dom.getAttribute("subTitle"))
		try:
			description = str(programs[x].childNodes[0].data)
		except AttributeError:
			description = "No Description"
		airdate = str(dom.getAttribute("airdate"))
		starttime = str(dom.getAttribute("startTime"))
		endtime = str(dom.getAttribute("endTime"))
		category = str(dom.getAttribute("category"))
		chanid = str(channels[x].getAttribute("chanId"))
		channame = str(channels[x].getAttribute("channelName"))
		callsign = str(channels[x].getAttribute("callSign"))
		
		if title not in titles:
			titles.append(title)
			idbanners[title] = GetSeriesIDBanner(title)
			shows[title] = []
		
		single = [title,subtitle,description,chanid,airdate,starttime,endtime]
		recordings.append(single)
		
		shows[title].append(single)
		
		x=x+1
		
	titles.sort()
	
	print "MythBoxee (LoadShows): Titles: " + ", ".join(titles)
	
	items = mc.ListItems()
	for title in titles:
		item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
		item.SetLabel(title)
		item.SetThumbnail(idbanners[title][1])
		item.SetProperty("seriesid", idbanners[title][0])
		items.append(item)

	mc.GetWindow(14000).GetList(13).SetItems(items)


def LoadSingleShow():
	config = mc.GetApp().GetLocalConfig()
	ilist = mc.GetActiveWindow().GetList(13)
	item = ilist.GetItem(ilist.GetFocusedItem())
	name = item.GetLabel()
	config.SetValue("seriesid", item.GetProperty("seriesid"))
	config.SetValue("show", name)
	mc.ActivateWindow(14001)
	
	SetSortables()
	GetSetSeriesDetails(name, item.GetProperty("seriesid"))
	LoadSeriesEpisodes(name)


def SetSortables():
	sortable = ['Original Air Date', 'Recorded Date', 'Title']
	items = mc.ListItems()
	for sorttype in sortable:
		item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
		item.SetLabel(sorttype)
		items.append(item)
	
	mc.GetActiveWindow().GetList(2014).SetItems(items)
	mc.GetActiveWindow().GetList(2014).SetSelected(0, True)
	
	sortableby = ['Ascending', 'Descending']	
	items = mc.ListItems()
	for sorttype in sortableby:
		item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
		item.SetLabel(sorttype)
		items.append(item)
		
	mc.GetActiveWindow().GetList(2015).SetItems(items)
	mc.GetActiveWindow().GetList(2015).SetSelected(1, True)


def SortBySeriesEpisodes():
	sortByItems = sortByItemNumber = mc.GetWindow(14001).GetList(2014).GetSelected()
	sortDirectionItems = sortDirectionItemNumber = mc.GetWindow(14001).GetList(2015).GetSelected()

	mc.GetActiveWindow().GetList(2014).UnselectAll()
	mc.GetActiveWindow().GetList(2014).SetSelected(mc.GetActiveWindow().GetList(2014).GetFocusedItem(), True)
	
	config.SetValue("SortBy", mc.GetActiveWindow().GetList(2014).GetItem(mc.GetActiveWindow().GetList(2014).GetFocusedItem()).GetLabel())
	
	LoadSeriesEpisodes(config.GetValue("name"))


def SortDirSeriesEpisodes():
	sortByItems = sortByItemNumber = mc.GetWindow(14001).GetList(2014).GetSelected()

	mc.GetActiveWindow().GetList(2015).UnselectAll()
	mc.GetActiveWindow().GetList(2015).SetSelected(mc.GetActiveWindow().GetList(2015).GetFocusedItem(), True)
	
	config.SetValue("SortDir", mc.GetActiveWindow().GetList(2015).GetItem(mc.GetActiveWindow().GetList(2015).GetFocusedItem()).GetLabel())

	LoadSeriesEpisodes(config.GetValue("name"))

def GetSeriesIDBanner(name):
	print "MythBoxee (GetSeriesIDBanner): " + name + " [" + "http://www.thetvdb.com/api/GetSeries.php?seriesname=" + name.replace(" ", "%20") + "]"
	sg = mc.Http()
	sg.SetUserAgent('MythBoxee v3.0.beta')
	html = sg.Get(str("http://www.thetvdb.com/api/GetSeries.php?seriesname=" + name.replace(" ", "%20")))
	series = re.compile("<seriesid>(.*?)</seriesid>").findall(html)
	banners = re.compile("<banner>(.*?)</banner>").findall(html)
	show = []
	try:
		show.append(series[0])
		show.append("http://www.thetvdb.com/banners/" + banners[0])
	except IndexError:
		show.append("00000")
		show.append("mb_artwork_error.png")
			
	return show


def GetSetSeriesDetails(name, seriesid):
	sg = mc.Http()
	sg.SetUserAgent('MythBoxee v3.0.beta')
	html = sg.Get("http://thetvdb.com/api/6BEAB4CB5157AAE0/series/" + seriesid + "/")
	overview = re.compile("<Overview>(.*?)</Overview>").findall(html)
	poster = re.compile("<poster>(.*?)</poster>").findall(html)
	items = mc.ListItems()
	item = mc.ListItem( mc.ListItem.MEDIA_UNKNOWN )
	item.SetLabel(name)
	item.SetTitle(name)
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

	mc.GetWindow(14001).GetList(21).SetItems(items)


def LoadSeriesEpisodes(name):
	config = mc.GetApp().GetLocalConfig()
	config.SetValue("name", name)
	showitems = mc.ListItems()

	sortBy = config.GetValue("SortBy")
	sortDir = config.GetValue("SortDir")

	print "MythBoxee (LoadSeriesEpisodes): " + name

	if sortBy == "Original Air Date" and sortDir == "Ascending":
		episodes = sorted(shows[name], key=itemgetter(4))
	elif sortBy == "Original Air Date" and sortDir == "Descending":
		episodes = sorted(shows[name], key=itemgetter(4), reverse=True)
	elif sortBy == "Recorded Date" and sortDir == "Ascending":
		episodes = sorted(shows[name], key=itemgetter(5))
	elif sortBy == "Recorded Date" and sortDir == "Descending":
		episodes = sorted(shows[name], key=itemgetter(5), reverse=True)
	elif sortBy == "Title" and sortDir == "Ascending":
		episodes = sorted(shows[name], key=itemgetter(1))
	elif sortBy == "Title" and sortDir == "Descending":
		episodes = sorted(shows[name], key=itemgetter(1), reverse=True)
	else:
		episodes = shows[name]

	for title,subtitle,desc,chanid,airdate,starttime,endtime in episodes:
		showitem = mc.ListItem( mc.ListItem.MEDIA_VIDEO_EPISODE )
		showitem.SetLabel(subtitle)
		showitem.SetTitle(subtitle)
		showitem.SetTVShowTitle(name)
		showitem.SetDescription(desc)
		date = airdate.split("-")
		showitem.SetProperty("starttime", starttime)
		showitem.SetDate(int(date[0]), int(date[1]), int(date[2]))
		showitem.SetThumbnail("http://" + config.GetValue("server") + ":6544/Myth/GetPreviewImage?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", "%20")) 
		showitem.SetPath("http://" + config.GetValue("server") + ":6544/Myth/GetRecording?ChanId=" + chanid + "&StartTime=" + starttime.replace("T", "%20"))
		showitems.append(showitem)

	mc.GetActiveWindow().GetList(2013).SetItems(showitems)
	


def GetServer():
	config = mc.GetApp().GetLocalConfig()
	server = config.GetValue("server")
	response = mc.ShowDialogKeyboard("Enter IP Address of MythTV Backend Server", server, False)
	url = "http://" + response + ":6544/Myth/GetConnectionInfo"
	if VerifyServer(url) == True:
		config.SetValue("server", response)

def VerifyServer(url):
	config = mc.GetApp().GetLocalConfig()
	http = mc.Http()
	data = http.Get(url)
	if http.GetHttpResponseCode() == 200:
		config.SetValue("verified", "1")
		return True
	else:
		return False









