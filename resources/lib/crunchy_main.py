# -*- coding: utf-8 -*-
"""
    CrunchyRoll;xbmc
    Copyright (C) 2012 - 2014 Matthew Beacher
    This program is free software; you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the
    Free Software Foundation; either version 2 of the License.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation,
Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

import re
import sys
import urllib

import xbmc
import xbmcgui
import xbmcplugin

import crunchy_json as crj



class updateArgs(object):

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.iteritems():
            if value == 'None':
                kwargs[key] = None
            else:
                kwargs[key] = urllib.unquote_plus(kwargs[key])
        self.__dict__.update(kwargs)



class UI(object):

    def __init__(self, addon=None):
        self.main   = Main(checkMode=False)
        self._addon = sys.modules['__main__'].__settings__
        self._lang  = sys.modules['__main__'].__language__
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')


    def endofdirectory(self, sortMethod='none'):
        # Set sortmethod to something xbmc can use
        if sortMethod == 'title':
            sortMethod = xbmcplugin.SORT_METHOD_LABEL
        elif sortMethod == 'none':
            sortMethod = xbmcplugin.SORT_METHOD_NONE
        elif sortMethod == 'date':
            sortMethod = xbmcplugin.SORT_METHOD_DATE

        # Sort methods are required in library mode
        xbmcplugin.addSortMethod(int(sys.argv[1]),
                                 sortMethod)

        # Let xbmc know the script is done adding items to the list
        dontAddToHierarchy = False
        xbmcplugin.endOfDirectory(handle        = int(sys.argv[1]),
                                  updateListing = dontAddToHierarchy)


    def addItem(self, info, isFolder=True, total_items=0):
        # Defaults in dict. Use 'None' instead of None so it is compatible for
        # quote_plus in parseArgs.
        info.setdefault('url',       'None')
        info.setdefault('Thumb',     'None')
        info.setdefault('Fanart_Image',
                        xbmc.translatePath(self._addon.getAddonInfo('fanart')))
        info.setdefault('mode',      'None')
        info.setdefault('count',     '0')
        info.setdefault('filterx',   'None')
        info.setdefault('id',        'None')
        info.setdefault('series_id', 'None')
        info.setdefault('offset',    '0')
        info.setdefault('season',    '1')
        info.setdefault('series_id', '0')
        info.setdefault('page_url',  'None')
        info.setdefault('complete',  'True')
        info.setdefault('showtype',  'None')
        info.setdefault('Title',     'None')
        info.setdefault('year',      '0')
        info.setdefault('playhead',  '0')
        info.setdefault('duration',  '0')
        info.setdefault('plot',      'None')

        # Create params for xbmcplugin module
        u = sys.argv[0]   +\
            '?url='       + urllib.quote_plus(info['url'])          +\
            '&mode='      + urllib.quote_plus(info['mode'])         +\
            '&name='      + urllib.quote_plus(info['Title'])        +\
            '&id='        + urllib.quote_plus(info['id'])           +\
            '&count='     + urllib.quote_plus(info['count'])        +\
            '&series_id=' + urllib.quote_plus(info['series_id'])    +\
            '&filterx='   + urllib.quote_plus(info['filterx'])      +\
            '&offset='    + urllib.quote_plus(info['offset'])       +\
            '&icon='      + urllib.quote_plus(info['Thumb'])        +\
            '&complete='  + urllib.quote_plus(info['complete'])     +\
            '&fanart='    + urllib.quote_plus(info['Fanart_Image']) +\
            '&season='    + urllib.quote_plus(info['season'])       +\
            '&showtype='  + urllib.quote_plus(info['showtype'])     +\
            '&year='      + urllib.quote_plus(info['year'])         +\
            '&playhead='  + urllib.quote_plus(info['playhead'])     +\
            '&duration='  + urllib.quote_plus(info['duration'])     +\
            '&plot='      + urllib.quote_plus(info['plot']          +'%20')

        # Create list item
        li = xbmcgui.ListItem(label          = info['Title'],
                              thumbnailImage = info['Thumb'])
        li.setInfo(type       = "Video",
                   infoLabels = {"Title": info['Title'],
                                 "Plot":  info['plot'],
                                 "Year":  info['year']})
        li.setProperty("Fanart_Image", info['Fanart_Image'])

        # For videos, replace context menu with queue and add to favorites
        if not isFolder:
            #li.setProperty("IsPlayable", "true")
            # Let xbmc know this can be played, unlike a folder.
            # Add context menu items to non-folder items.
            rex = re.compile(r'mode=[a-z_]*[^&]')
            s1  = re.sub(rex, 'mode=add_to_queue', u)
            s2  = re.sub(rex, 'mode=remove_from_queue', u)

            contextmenu = [('Queue Video',     'XBMC.Action(Queue)'),
                           ('Enqueue Series',  'XBMC.RunPlugin(%s)' % s1),
                           ('Dequeue Series',  'XBMC.RunPlugin(%s)' % s2),
                           ('Add-on settings', 'XBMC.Addon.OpenSettings(%s)' % self._addon.getAddonInfo('id'))]

            li.addContextMenuItems(contextmenu, replaceItems=True)

        # For folders, completely remove contextmenu, as it is totally useless
        else:
            li.addContextMenuItems([], replaceItems=True)

        # Add item to list
        xbmcplugin.addDirectoryItem(handle     = int(sys.argv[1]),
                                    url        = u,
                                    listitem   = li,
                                    isFolder   = isFolder,
                                    totalItems = total_items)


    def showMain(self):
        change_language = self._addon.getSetting("change_language")

        if crj.CrunchyJSON() is False:
            self.addItem({'Title': 'Session Failed: Check Login'})
            self.endofdirectory()
        else:
            if change_language != "0":
                crj.CrunchyJSON().changeLocale()

            Anime   = self._lang(30100).encode("utf8")
            Drama   = self._lang(30104).encode("utf8")
            Queue   = self._lang(30105).encode("utf8")
            History = self._lang(30111).encode("utf8")

            self.addItem({'Title':    Queue,
                          'mode':     'queue'})
            self.addItem({'Title':    History,
                          'mode':     'History'})
            self.addItem({'Title':    Anime,
                          'mode':     'Channels',
                          'showtype': 'Anime'})
            self.addItem({'Title':    Drama,
                          'mode':     'Channels',
                          'showtype': 'Drama'})
            self.endofdirectory()


    def channels(self):
        popular         = self._lang(30103).encode("utf8")
        Simulcasts      = self._lang(30106).encode("utf8")
        Recently_Added  = self._lang(30102).encode("utf8")
        alpha           = self._lang(30112).encode("utf8")
        Browse_by_Genre = self._lang(30107).encode("utf8")
        seasons         = self._lang(30110).encode("utf8")

        showtype        = self.main.args.showtype

        self.addItem({'Title':    popular,
                      'mode':     'list_series',
                      'showtype': showtype,
                      'filterx':  'popular',
                      'offset':   '0'})
        self.addItem({'Title':    Simulcasts,
                      'mode':     'list_series',
                      'showtype': showtype,
                      'filterx':  'simulcast',
                      'offset':   '0'})
        self.addItem({'Title':    Recently_Added,
                      'mode':     'list_series',
                      'showtype': showtype,
                      'filterx':  'updated',
                      'offset':   '0'})
        self.addItem({'Title':    alpha,
                      'mode':     'list_series',
                      'showtype': showtype,
                      'filterx':  'alpha',
                      'offset':   '0'})
        self.addItem({'Title':    Browse_by_Genre,
                      'mode':     'list_categories',
                      'showtype': showtype,
                      'filterx':  'genre',
                      'offset':   '0'})
        self.addItem({'Title':    seasons,
                      'mode':     'list_categories',
                      'showtype': showtype,
                      'filterx':  'season',
                      'offset':   '0'})
        self.endofdirectory()


    def json_list_series(self):
        crj.CrunchyJSON().list_series(self.main.args.name,
                                      self.main.args.showtype,
                                      self.main.args.filterx,
                                      self.main.args.offset)


    def json_list_cat(self):
        crj.CrunchyJSON().list_categories(self.main.args.name,
                                          self.main.args.showtype,
                                          self.main.args.filterx)


    def json_list_collection(self):
        crj.CrunchyJSON().list_collections(self.main.args.series_id,
                                           self.main.args.name,
                                           self.main.args.count,
                                           self.main.args.icon,
                                           self.main.args.fanart)


    def json_list_media(self):
        crj.CrunchyJSON().list_media(self.main.args.id,
                                     self.main.args.filterx,
                                     self.main.args.count,
                                     self.main.args.complete,
                                     self.main.args.season,
                                     self.main.args.fanart)


    def json_History(self):
        """Display Crunchyroll history.

        """
        crj.CrunchyJSON().History()


    def queue(self):
        """Display Crunchyroll queue.

        """
        crj.CrunchyJSON().Queue()


    def add_to_queue(self):
        """Add selected video series to queue at Crunchyroll.

        """
        # Get series_id
        options = {'media_id': self.main.args.id,
                   'fields':   "series.series_id"}
        request = crj.CrunchyJSON.makeAPIRequest(crj.CrunchyJSON(),
                                                 'info',
                                                 options)

        series_id = request['data']['series_id']

        # Add the series to queue at CR if it is not there already
        options = {'series_id': series_id,
                   'fields':    "series.series_id"}
        request = crj.CrunchyJSON.makeAPIRequest(crj.CrunchyJSON(),
                                                 'queue',
                                                 options)

        for col in request['data']:
            if series_id == col['series']['series_id']:
                return

        options = {'series_id': series_id}

        request = crj.CrunchyJSON.makeAPIRequest(crj.CrunchyJSON(),
                                                 'add_to_queue',
                                                 options)

        xbmc.log("CR: add_to_queue: request['error'] = "
                 + str(request['error']))


    def remove_from_queue(self):
        """Remove selected video series from queue at Crunchyroll.

        """
        # Get series_id
        options = {'media_id': self.main.args.id,
                   'fields':   "series.series_id"}
        request = crj.CrunchyJSON.makeAPIRequest(crj.CrunchyJSON(),
                                                 'info',
                                                 options)

        series_id = request['data']['series_id']

        # Remove the series from queue at CR if it is there
        options = {'series_id': series_id,
                   'fields':    "series.series_id"}
        request = crj.CrunchyJSON.makeAPIRequest(crj.CrunchyJSON(),
                                                 'queue',
                                                 options)

        for col in request['data']:
            if series_id == col['series']['series_id']:
                options = {'series_id': series_id}

                request = crj.CrunchyJSON.makeAPIRequest(crj.CrunchyJSON(),
                                                         'remove_from_queue',
                                                         options)

                xbmc.log("CR: remove_from_queue: request['error'] = "
                         + str(request['error']))


    def startVideo(self):
        crj.CrunchyJSON().startPlayback(self.main.args.name,
                                        self.main.args.id,
                                        self.main.args.duration,
                                        self.main.args.icon)


    def Fail(self):
        badstuff = self._lang(30207).encode("utf8")

        self.addItem({'Title': badstuff,
                      'mode':  'Fail'})

        xbmc.log("CR: Main: checkMode fall through", xbmc.LOGWARNING)

        self.endofdirectory()



class Main(object):

    def __init__(self, checkMode=True):

        crj.CrunchyJSON()

        self.parseArgs()
        if checkMode:
            self.checkMode()


    def parseArgs(self):
        # Call updateArgs() with our formatted argv to create self.args object
        if (sys.argv[2]):
            exec("self.args = updateArgs(%s')"
                 % (sys.argv[2][1:].replace('&', "',").replace('=', "='")))
        else:
            # updateArgs will turn the 'None' into None.
            # Don't simply define it as None because unquote_plus in updateArgs
            # will throw an exception.
            # This is a pretty ugly solution.
            self.args = updateArgs(mode = 'None',
                                   url  = 'None',
                                   name = 'None')


    def checkMode(self):
        mode = self.args.mode
        xbmc.log("CR: Main: argv[0] = %s" % sys.argv[0])
        xbmc.log("CR: Main: argv[1] = %s" % sys.argv[1])
        xbmc.log("CR: Main: argv[2] = %s" % sys.argv[2])
        xbmc.log("CR: Main: args = %s" % str(self.args.__dict__))
        xbmc.log("CR: Main: mode = %s" % mode)
        if mode is None:
            UI().showMain()
        elif mode == 'Channels':
            UI().channels()
        elif mode == 'list_series':
            UI().json_list_series()
        elif mode == 'list_categories':
            UI().json_list_cat()
        elif mode == 'list_coll':
            UI().json_list_collection()
        elif mode == 'list_media':
            UI().json_list_media()
        elif mode == 'History':
            UI().json_History()
        elif mode == 'queue':
            UI().queue()
        elif mode == 'add_to_queue':
            UI().add_to_queue()
        elif mode == 'remove_from_queue':
            UI().remove_from_queue()
        elif mode == 'videoplay':
            UI().startVideo()
        else:
            UI().Fail()
