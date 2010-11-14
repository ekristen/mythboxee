#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""Simple-to-use Python interface to The TVDB's API (www.thetvdb.com)

Example usage:

>>> from tvdb_api import Tvdb
>>> t = Tvdb()
>>> t['Lost'][4][11]['episodename']
u'Cabin Fever'
"""
__author__ = "dbr/Ben"
__version__ = "1.2.1"

import os
import sys
import urllib
import urllib2
import tempfile
import logging

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

from cache import CacheHandler

from tvdb_ui import BaseUI, ConsoleUI
from tvdb_exceptions import (tvdb_error, tvdb_userabort, tvdb_shownotfound,
    tvdb_seasonnotfound, tvdb_episodenotfound, tvdb_attributenotfound)

class ShowContainer(dict):
    """Simple dict that holds a series of Show instances
    """
    pass


class Show(dict):
    """Holds a dict of seasons, and show data.
    """
    def __init__(self):
        dict.__init__(self)
        self.data = {}

    def __repr__(self):
        return "<Show %s (containing %s seasons)>" % (
            self.data.get(u'seriesname', 'instance'),
            len(self)
        )

    def __getitem__(self, key):
        if key in self:
            # Key is an episode, return it
            return dict.__getitem__(self, key)

        if key in self.data:
            # Non-numeric request is for show-data
            return dict.__getitem__(self.data, key)

        # Data wasn't found, raise appropriate error
        if isinstance(key, int) or key.isdigit():
            # Episode number x was not found
            raise tvdb_seasonnotfound("Could not find season %s" % (repr(key)))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise tvdb_attributenotfound("Cannot find attribute %s" % (repr(key)))

    def search(self, term = None, key = None):
        """
        Search all episodes in show. Can search all data, or a specific key (for
        example, episodename)

        Always returns an array (can be empty). First index contains the first
        match, and so on.

        Each array index is an Episode() instance, so doing
        search_results[0]['episodename'] will retrieve the episode name of the
        first match.

        Search terms are converted to lower case (unicode) strings.

        # Examples

        These examples assume t is an instance of Tvdb():

        >>> t = Tvdb()
        >>>

        To search for all episodes of Scrubs with a bit of data
        containing "my first day":

        >>> t['Scrubs'].search("my first day")
        [<Episode 01x01 - My First Day>]
        >>>

        Search for "My Name Is Earl" episode named "Faked His Own Death":

        >>> t['My Name Is Earl'].search('Faked His Own Death', key = 'episodename')
        [<Episode 01x04 - Faked His Own Death>]
        >>>

        To search Scrubs for all episodes with "mentor" in the episode name:

        >>> t['scrubs'].search('mentor', key = 'episodename')
        [<Episode 01x02 - My Mentor>, <Episode 03x15 - My Tormented Mentor>]
        >>>

        # Using search results

        >>> results = t['Scrubs'].search("my first")
        >>> print results[0]['episodename']
        My First Day
        >>> for x in results: print x['episodename']
        My First Day
        My First Step
        My First Kill
        >>>
        """
        results = []
        for cur_season in self.values():
            searchresult = cur_season.search(term = term, key = key)
            if len(searchresult) != 0:
                results.extend(searchresult)
        #end for cur_season
        return results


class Season(dict):
    def __repr__(self):
        return "<Season instance (containing %s episodes)>" % (
            len(self.keys())
        )

    def __getitem__(self, episode_number):
        if episode_number not in self:
            raise tvdb_episodenotfound("Could not find episode %s" % (repr(episode_number)))
        else:
            return dict.__getitem__(self, episode_number)

    def search(self, term = None, key = None):
        """Search all episodes in season, returns a list of matching Episode
        instances.

        >>> t = Tvdb()
        >>> t['scrubs'][1].search('first day')
        [<Episode 01x01 - My First Day>]
        >>>

        See Show.search documentation for further information on search
        """
        results = []
        for ep in self.values():
            searchresult = ep.search(term = term, key = key)
            if searchresult is not None:
                results.append(
                    searchresult
                )
        return results


class Episode(dict):
    def __repr__(self):
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname is not None:
            return "<Episode %02dx%02d - %s>" % (seasno, epno, epname)
        else:
            return "<Episode %02dx%02d>" % (seasno, epno)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise tvdb_attributenotfound("Cannot find attribute %s" % (repr(key)))

    def search(self, term = None, key = None):
        """Search episode data for term, if it matches, return the Episode (self).
        The key parameter can be used to limit the search to a specific element,
        for example, episodename.

        This primarily for use use by Show.search and Season.search. See
        Show.search for further information on search

        Simple example:

        >>> e = Episode()
        >>> e['episodename'] = "An Example"
        >>> e.search("examp")
        <Episode 00x00 - An Example>
        >>>

        Limiting by key:

        >>> e.search("examp", key = "episodename")
        <Episode 00x00 - An Example>
        >>>
        """
        if term == None:
            raise TypeError("must supply string to search for (contents)")

        term = unicode(term).lower()
        for cur_key, cur_value in self.items():
            cur_key, cur_value = unicode(cur_key).lower(), unicode(cur_value).lower()
            if key is not None and cur_key != key:
                # Do not search this key
                continue
            if cur_value.find( unicode(term).lower() ) > -1:
                return self
            #end if cur_value.find()
        #end for cur_key, cur_value


class Actors(list):
    """Holds all Actor instances for a show
    """
    pass


class Actor(dict):
    """Represents a single actor. Should contain..

    id,
    image,
    name,
    role,
    sortorder
    """
    def __repr__(self):
        return "<Actor \"%s\">" % (self.get("name"))


class Tvdb:
    """Create easy-to-use interface to name of season/episode name
    >>> t = Tvdb()
    >>> t['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """
    def __init__(self,
                interactive = False,
                select_first = False,
                debug = False,
                cache = True,
                banners = False,
                actors = False,
                custom_ui = None,
                language = None,
                search_all_languages = False,
                apikey = None):
        """interactive (True/False):
            When True, uses built-in console UI is used to select the correct show.
            When False, the first search result is used.

        select_first (True/False):
            Automatically selects the first series search result (rather
            than showing the user a list of more than one series).
            Is overridden by interactive = False, or specifying a custom_ui

        debug (True/False):
             shows verbose debugging information

        cache (True/False/str/unicode):
            Retrieved XML are persisted to to disc. If true, stores in tvdb_api
            folder under your systems TEMP_DIR, if set to str/unicode instance it
            will use this as the cache location. If False, disables caching.

        banners (True/False):
            Retrieves the banners for a show. These are accessed
            via the _banners key of a Show(), for example:

            >>> Tvdb(banners=True)['scrubs']['_banners'].keys()
            ['fanart', 'poster', 'series', 'season']

        actors (True/False):
            Retrieves a list of the actors for a show. These are accessed
            via the _actors key of a Show(), for example:

            >>> t = Tvdb(actors=True)
            >>> t['scrubs']['_actors'][0]['name']
            u'Zach Braff'

        custom_ui (tvdb_ui.BaseUI subclass):
            A callable subclass of tvdb_ui.BaseUI (overrides interactive option)

        language (2 character language abbreviation):
            The language of the returned data. Is also the language search
            uses. Default is "en" (English). For full list, run..

            >>> Tvdb().config['valid_languages'] #doctest: +ELLIPSIS
            ['da', 'fi', 'nl', ...]

        search_all_languages (True/False):
            By default, Tvdb will only search in the language specified using
            the language option. When this is True, it will search for the
            show in and language

        apikey (str/unicode):
            Override the default thetvdb.com API key. By default it will use
            tvdb_api's own key (fine for small scripts), but you can use your
            own key if desired - this is recommended if you are embedding
            tvdb_api in a larger application)
            See http://thetvdb.com/?tab=apiregister to get your own key
        """
        self.shows = ShowContainer() # Holds all Show classes
        self.corrections = {} # Holds show-name to show_id mapping

        self.config = {}

        if apikey is not None:
            self.config['apikey'] = apikey
        else:
            self.config['apikey'] = "0629B785CE550C8D" # tvdb_api's API key

        self.config['debug_enabled'] = debug # show debugging messages

        self.config['custom_ui'] = custom_ui

        self.config['interactive'] = interactive # prompt for correct series?

        self.config['select_first'] = select_first

        self.config['search_all_languages'] = search_all_languages

        if cache is True:
            self.config['cache_enabled'] = True
            self.config['cache_location'] = self._getTempDir()
        elif isinstance(cache, basestring):
            self.config['cache_enabled'] = True
            self.config['cache_location'] = cache
        else:
            self.config['cache_enabled'] = False

        if self.config['cache_enabled']:
            self.urlopener = urllib2.build_opener(
                CacheHandler(self.config['cache_location'])
            )
        else:
            self.urlopener = urllib2.build_opener()

        self.config['banners_enabled'] = banners
        self.config['actors_enabled'] = actors

        self.log = self._initLogger() # Setups the logger (self.log.debug() etc)

        # List of language from http://www.thetvdb.com/api/0629B785CE550C8D/languages.xml
        # Hard-coded here as it is realtively static, and saves another HTTP request, as
        # recommended on http://thetvdb.com/wiki/index.php/API:languages.xml
        self.config['valid_languages'] = [
            "da", "fi", "nl", "de", "it", "es", "fr","pl", "hu","el","tr",
            "ru","he","ja","pt","zh","cs","sl", "hr","ko","en","sv","no"
        ]

        if language is None:
            self.config['language'] = "en"
        elif language not in self.config['valid_languages']:
            raise ValueError("Invalid language %s, options are: %s" % (
                language, self.config['valid_languages']
            ))
        else:
            self.config['language'] = language

        # The following url_ configs are based of the
        # http://thetvdb.com/wiki/index.php/Programmers_API
        self.config['base_url'] = "http://www.thetvdb.com"

        if self.config['search_all_languages']:
            self.config['url_getSeries'] = "%(base_url)s/api/GetSeries.php?seriesname=%%s&language=all" % self.config
        else:
            self.config['url_getSeries'] = "%(base_url)s/api/GetSeries.php?seriesname=%%s&language=%(language)s" % self.config

        self.config['url_epInfo'] = "%(base_url)s/api/%(apikey)s/series/%%s/all/%(language)s.xml" % self.config

        self.config['url_seriesInfo'] = "%(base_url)s/api/%(apikey)s/series/%%s/%(language)s.xml" % self.config
        self.config['url_actorsInfo'] = "%(base_url)s/api/%(apikey)s/series/%%s/actors.xml" % self.config

        self.config['url_seriesBanner'] = "%(base_url)s/api/%(apikey)s/series/%%s/banners.xml" % self.config
        self.config['url_artworkPrefix'] = "%(base_url)s/banners/%%s" % self.config

    #end __init__

    def _initLogger(self):
        """Setups a logger using the logging module, returns a log object
        """
        logger = logging.getLogger("tvdb")
        formatter = logging.Formatter('%(asctime)s) %(levelname)s %(message)s')

        hdlr = logging.StreamHandler(sys.stdout)

        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)

        if self.config['debug_enabled']:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.WARNING)
        return logger
    #end initLogger

    def _getTempDir(self):
        """Returns the [system temp dir]/tvdb_api
        """
        import mc
        return mc.GetTempDir()
        return os.path.join(tempfile.gettempdir(), "tvdb_api")

    def _loadUrl(self, url, recache = False):
        try:
            self.log.debug("Retrieving URL %s" % url)
            resp = self.urlopener.open(url)
            if 'x-local-cache' in resp.headers:
                self.log.debug("URL %s was cached in %s" % (
                    url,
                    resp.headers['x-local-cache'])
                )
                if recache:
                    self.log.debug("Attempting to recache %s" % url)
                    resp.recache()
        except urllib2.URLError, errormsg:
            raise tvdb_error("Could not connect to server: %s" % (errormsg))
        #end try

        return resp.read()

    def _getetsrc(self, url):
        """Loads a URL sing caching, returns an ElementTree of the source
        """
        src = self._loadUrl(url)
        try:
            return ElementTree.fromstring(src)
        except SyntaxError:
            src = self._loadUrl(url, recache=True)
            try:
                return ElementTree.fromstring(src)
            except SyntaxError, exceptionmsg:
                errormsg = "There was an error with the XML retrieved from thetvdb.com:\n%s" % (
                    exceptionmsg
                )

                if self.config['cache_enabled']:
                    errormsg += "\nFirst try emptying the cache folder at..\n%s" % (
                        self.config['cache_location']
                    )

                errormsg += "\nIf this does not resolve the issue, please try again later. If the error persists, report a bug on"
                errormsg += "\nhttp://dbr.lighthouseapp.com/projects/13342-tvdb_api/overview\n"
                raise tvdb_error(errormsg)
    #end _getetsrc

    def _setItem(self, sid, seas, ep, attrib, value):
        """Creates a new episode, creating Show(), Season() and
        Episode()s as required. Called by _getShowData to populute

        Since the nice-to-use tvdb[1][24]['name] interface
        makes it impossible to do tvdb[1][24]['name] = "name"
        and still be capable of checking if an episode exists
        so we can raise tvdb_shownotfound, we have a slightly
        less pretty method of setting items.. but since the API
        is supposed to be read-only, this is the best way to
        do it!
        The problem is that calling tvdb[1][24]['episodename'] = "name"
        calls __getitem__ on tvdb[1], there is no way to check if
        tvdb.__dict__ should have a key "1" before we auto-create it
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        if seas not in self.shows[sid]:
            self.shows[sid][seas] = Season()
        if ep not in self.shows[sid][seas]:
            self.shows[sid][seas][ep] = Episode()
        self.shows[sid][seas][ep][attrib] = value
    #end _set_item

    def _setShowData(self, sid, key, value):
        """Sets self.shows[sid] to a new Show instance, or sets the data
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        self.shows[sid].data[key] = value

    def _cleanData(self, data):
        """Cleans up strings returned by TheTVDB.com

        Issues corrected:
        - Replaces &amp; with &
        - Trailing whitespace
        """
        data = data.replace(u"&amp;", u"&")
        data = data.strip()
        return data
    #end _cleanData

    def _getSeries(self, series):
        """This searches TheTVDB.com for the series name,
        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.
        """
        series = urllib.quote(series.encode("utf-8"))
        self.log.debug("Searching for show %s" % series)
        seriesEt = self._getetsrc(self.config['url_getSeries'] % (series))
        allSeries = []
        for series in seriesEt:
            sn = series.find('SeriesName')
            value = self._cleanData(sn.text)
            cur_sid = series.find('id').text
            self.log.debug('Found series %s (id: %s)' % (value, cur_sid))
            allSeries.append( {'sid':cur_sid, 'name':value} )
        #end for series

        if len(allSeries) == 0:
            self.log.debug('Series result returned zero')
            raise tvdb_shownotfound("Show-name search returned zero results (cannot find show on TVDB)")

        if self.config['custom_ui'] is not None:
            self.log.debug("Using custom UI %s" % (repr(self.config['custom_ui'])))
            ui = self.config['custom_ui'](config = self.config, log = self.log)
        else:
            if not self.config['interactive']:
                self.log.debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config = self.config, log = self.log)
            else:
                self.log.debug('Interactivily selecting show using ConsoleUI')
                ui = ConsoleUI(config = self.config, log = self.log)
            #end if config['interactive]
        #end if custom_ui != None

        return ui.selectSeries(allSeries)

    #end _getSeries

    def _parseBanners(self, sid):
        """Parses banners XML, from
        http://www.thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml

        Banners are retrieved using t['show name]['_banners'], for example:

        >>> t = Tvdb(banners = True)
        >>> t['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        'http://www.thetvdb.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        self.log.debug('Getting season banners for %s' % (sid))
        bannersEt = self._getetsrc( self.config['url_seriesBanner'] % (sid) )
        banners = {}
        for cur_banner in bannersEt.findall('Banner'):
            bid = cur_banner.find('id').text
            btype = cur_banner.find('BannerType')
            btype2 = cur_banner.find('BannerType2')
            if btype is None or btype2 is None:
                continue
            btype, btype2 = btype.text, btype2.text
            if not btype in banners:
                banners[btype] = {}
            if not btype2 in banners[btype]:
                banners[btype][btype2] = {}
            if not bid in banners[btype][btype2]:
                banners[btype][btype2][bid] = {}

            self.log.debug("Banner: %s", bid)
            for cur_element in cur_banner.getchildren():
                tag = cur_element.tag.lower()
                value = cur_element.text
                if tag is None or value is None:
                    continue
                tag, value = tag.lower(), value.lower()
                self.log.debug("Banner info: %s = %s" % (tag, value))
                banners[btype][btype2][bid][tag] = value

            for k, v in banners[btype][btype2][bid].items():
                if k.endswith("path"):
                    new_key = "_%s" % (k)
                    self.log.debug("Transforming %s to %s" % (k, new_key))
                    new_url = self.config['url_artworkPrefix'] % (v)
                    self.log.debug("New banner URL: %s" % (new_url))
                    banners[btype][btype2][bid][new_key] = new_url

        self._setShowData(sid, "_banners", banners)


    # Alternate tvdb_api's method for retrieving graphics URLs but returned as a list that preserves
    # the user rating order highest rated to lowest rated
    def ttvdb_parseBanners(self, sid):
	    """Parses banners XML, from
	    http://www.thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml

	    Banners are retrieved using t['show name]['_banners'], for example:

	    >>> t = Tvdb(banners = True)
	    >>> t['scrubs']['_banners'].keys()
	    ['fanart', 'poster', 'series', 'season']
	    >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
	    'http://www.thetvdb.com/banners/posters/76156-2.jpg'
	    >>>

	    Any key starting with an underscore has been processed (not the raw
	    data from the XML)

	    This interface will be improved in future versions.
	    Changed in this interface is that a list or URLs is created to preserve the user rating order from
	    top rated to lowest rated.
	    """

	    self.log.debug('Getting season banners for %s' % (sid))
	    bannersEt = self._getetsrc( self.config['url_seriesBanner'] % (sid) )
	    banners = {}
	    bid_order = {'fanart': [], 'poster': [], 'series': [], 'season': []}
	    for cur_banner in bannersEt.findall('Banner'):
		    bid = cur_banner.find('id').text
		    btype = cur_banner.find('BannerType')
		    btype2 = cur_banner.find('BannerType2')
		    if btype is None or btype2 is None:
			    continue
		    btype, btype2 = btype.text, btype2.text
		    if not btype in banners:
			    banners[btype] = {}
		    if not btype2 in banners[btype]:
			    banners[btype][btype2] = {}
		    if not bid in banners[btype][btype2]:
			    banners[btype][btype2][bid] = {}
			    if btype in bid_order.keys():
				    if btype2 != u'blank':
					    bid_order[btype].append([bid, btype2])

		    self.log.debug("Banner: %s", bid)
		    for cur_element in cur_banner.getchildren():
			    tag = cur_element.tag.lower()
			    value = cur_element.text
			    if tag is None or value is None:
				    continue
			    tag, value = tag.lower(), value.lower()
			    self.log.debug("Banner info: %s = %s" % (tag, value))
			    banners[btype][btype2][bid][tag] = value

		    for k, v in banners[btype][btype2][bid].items():
			    if k.endswith("path"):
				    new_key = "_%s" % (k)
				    self.log.debug("Transforming %s to %s" % (k, new_key))
				    new_url = self.config['url_artworkPrefix'] % (v)
				    self.log.debug("New banner URL: %s" % (new_url))
				    banners[btype][btype2][bid][new_key] = new_url

	    graphics_in_order = {'fanart': [], 'poster': [], 'series': [], 'season': []}
	    for key in bid_order.keys():
		    for bid in bid_order[key]:
			    graphics_in_order[key].append(banners[key][bid[1]][bid[0]])
	    return graphics_in_order
    # end ttvdb_parseBanners()


    def _parseActors(self, sid):
        """Parsers actors XML, from
        http://www.thetvdb.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> t = Tvdb(actors = True)
        >>> actors = t['scrubs']['_actors']
        >>> type(actors)
        <class 'tvdb_api.Actors'>
        >>> type(actors[0])
        <class 'tvdb_api.Actor'>
        >>> actors[0]
        <Actor "Zach Braff">
        >>> sorted(actors[0].keys())
        ['id', 'image', 'name', 'role', 'sortorder']
        >>> actors[0]['name']
        u'Zach Braff'
        >>> actors[0]['image']
        'http://www.thetvdb.com/banners/actors/43640.jpg'

        Any key starting with an underscore has been processed (not the raw
        data from the XML)
        """
        self.log.debug("Getting actors for %s" % (sid))
        actorsEt = self._getetsrc(self.config['url_actorsInfo'] % (sid))

        cur_actors = Actors()
        for curActorItem in actorsEt.findall("Actor"):
            curActor = Actor()
            for curInfo in curActorItem:
                tag = curInfo.tag.lower()
                value = curInfo.text
                if value is not None:
                    if tag == "image":
                        value = self.config['url_artworkPrefix'] % (value)
                    else:
                        value = self._cleanData(value)
                curActor[tag] = value
            cur_actors.append(curActor)
        self._setShowData(sid, '_actors', cur_actors)

    def _getShowData(self, sid):
        """Takes a series ID, gets the epInfo URL and parses the TVDB
        XML file into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """

        # Parse show information
        self.log.debug('Getting all series data for %s' % (sid))
        seriesInfoEt = self._getetsrc(self.config['url_seriesInfo'] % (sid))
        for curInfo in seriesInfoEt.findall("Series")[0]:
            tag = curInfo.tag.lower()
            value = curInfo.text

            if value is not None:
                if tag in ['banner', 'fanart', 'poster']:
                    value = self.config['url_artworkPrefix'] % (value)
                else:
                    value = self._cleanData(value)

            self._setShowData(sid, tag, value)
            self.log.debug("Got info: %s = %s" % (tag, value))
        #end for series

        # Parse banners
        if self.config['banners_enabled']:
            self._parseBanners(sid)

        # Parse actors
        if self.config['actors_enabled']:
            self._parseActors(sid)

        # Parse episode data
        self.log.debug('Getting all episodes of %s' % (sid))
        epsEt = self._getetsrc( self.config['url_epInfo'] % (sid) )

        for cur_ep in epsEt.findall("Episode"):
            seas_no = int(cur_ep.find('SeasonNumber').text)
            ep_no = int(cur_ep.find('EpisodeNumber').text)
            for cur_item in cur_ep.getchildren():
                tag = cur_item.tag.lower()
                value = cur_item.text
                if value is not None:
                    if tag == 'filename':
                        value = self.config['url_artworkPrefix'] % (value)
                    else:
                        value = self._cleanData(value)
                self._setItem(sid, seas_no, ep_no, tag, value)
        #end for cur_ep
    #end _geEps

    def _nameToSid(self, name):
        """Takes show name, returns the correct series ID (if the show has
        already been grabbed), or grabs all episodes and returns
        the correct SID.
        """
        if name in self.corrections:
            self.log.debug('Correcting %s to %s' % (name, self.corrections[name]) )
            sid = self.corrections[name]
        else:
            self.log.debug('Getting show %s' % (name))
            selected_series = self._getSeries( name )
            sname, sid = selected_series['name'], selected_series['sid']
            self.log.debug('Got %s, sid %s' % (sname, sid))

            self.corrections[name] = sid
            self._getShowData(sid)
        #end if name in self.corrections
        return sid
    #end _nameToSid

    def __getitem__(self, key):
        """Handles tvdb_instance['seriesname'] calls.
        The dict index should be the show id
        """
        if isinstance(key, (int, long)):
            # Item is integer, treat as show id
            if key not in self.shows:
                self._getShowData(key)
            return self.shows[key]

        key = key.lower() # make key lower case
        sid = self._nameToSid(key)
        self.log.debug('Got series id %s' % (sid))
        return self.shows[sid]
    #end __getitem__

    def __repr__(self):
        return str(self.shows)
    #end __repr__
#end Tvdb

def main():
    """Simple example of using tvdb_api - it just
    grabs an episode name interactively.
    """
    tvdb_instance = Tvdb(interactive=True, debug=True, cache=False)
    print tvdb_instance['Lost']['seriesname']
    print tvdb_instance['Lost'][1][4]['episodename']

if __name__ == '__main__':
    main()
