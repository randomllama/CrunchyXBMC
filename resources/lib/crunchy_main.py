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

from crunchy_json import log



class updateArgs(object):

    def __init__(self, *args, **kwargs):
        """Initialize arguments object.

        Hold also references to the addon which can't be kept at module level.
        """
        self._addon = sys.modules['__main__'].__settings__
        self._lang  = encode(sys.modules['__main__'].__language__)
        self._id    = self._addon.getAddonInfo('id')

        for key, value in kwargs.iteritems():
            if value == 'None':
                kwargs[key] = None
            else:
                kwargs[key] = urllib.unquote_plus(kwargs[key])
        self.__dict__.update(kwargs)



def encode(f):
    """Decorator for encoding strings.

    """
    def lang_encoded(*args):
        return f(*args).encode('utf8')
    return lang_encoded


def endofdirectory(sortMethod='none'):
    """Mark end of directory listing.

    """
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


def addItem(args,
            info,
            isFolder=True,
            total_items=0,
            queued=False,
            rex=re.compile(r'(?<=mode=)[^&]*')):
    """Add item to directory listing.

    """
    # Defaults in dict. Use 'None' instead of None so it is compatible for
    # quote_plus in parseArgs.
    info.setdefault('url',          'None')
    info.setdefault('Thumb',        'None')
    info.setdefault('Fanart_Image',
                    xbmc.translatePath(args._addon.getAddonInfo('fanart')))
    info.setdefault('mode',         'None')
    info.setdefault('count',        '0')
    info.setdefault('filterx',      'None')
    info.setdefault('id',           'None')
    info.setdefault('series_id',    'None')
    info.setdefault('offset',       '0')
    info.setdefault('season',       '1')
    info.setdefault('series_id',    '0')
    info.setdefault('page_url',     'None')
    info.setdefault('complete',     'True')
    info.setdefault('media_type',   'None')
    info.setdefault('Title',        'None')
    info.setdefault('year',         '0')
    info.setdefault('playhead',     '0')
    info.setdefault('duration',     '0')
    info.setdefault('plot',         'None')

    # Create params for xbmcplugin module
    u = sys.argv[0]    +\
        '?url='        + urllib.quote_plus(info['url'])          +\
        '&mode='       + urllib.quote_plus(info['mode'])         +\
        '&name='       + urllib.quote_plus(info['Title'])        +\
        '&id='         + urllib.quote_plus(info['id'])           +\
        '&count='      + urllib.quote_plus(info['count'])        +\
        '&series_id='  + urllib.quote_plus(info['series_id'])    +\
        '&filterx='    + urllib.quote_plus(info['filterx'])      +\
        '&offset='     + urllib.quote_plus(info['offset'])       +\
        '&icon='       + urllib.quote_plus(info['Thumb'])        +\
        '&complete='   + urllib.quote_plus(info['complete'])     +\
        '&fanart='     + urllib.quote_plus(info['Fanart_Image']) +\
        '&season='     + urllib.quote_plus(info['season'])       +\
        '&media_type=' + urllib.quote_plus(info['media_type'])   +\
        '&year='       + urllib.quote_plus(info['year'])         +\
        '&playhead='   + urllib.quote_plus(info['playhead'])     +\
        '&duration='   + urllib.quote_plus(info['duration'])     +\
        '&plot='       + urllib.quote_plus(info['plot']          +'%20')

    # Create list item
    li = xbmcgui.ListItem(label          = info['Title'],
                          thumbnailImage = info['Thumb'])
    li.setInfo(type       = "Video",
               infoLabels = {"Title": info['Title'],
                             "Plot":  info['plot'],
                             "Year":  info['year']})
    li.setProperty("Fanart_Image", info['Fanart_Image'])

    # Add context menu
    s1  = re.sub(rex, 'add_to_queue',      u)
    s2  = re.sub(rex, 'remove_from_queue', u)

    cm = [('Add-on settings', 'XBMC.Addon.OpenSettings(%s)' % args._id)]

    if (args.mode is not None and
        args.mode not in 'Channels|list_categories'):

        cm.insert(0, ('Queue Video', 'XBMC.Action(Queue)'))

    if not isFolder:
        # Let XBMC know this can be played, unlike a folder
        li.setProperty('IsPlayable', 'true')

        if queued:
            cm.insert(1, ('Dequeue Series', 'XBMC.RunPlugin(%s)' % s2))
        else:
            cm.insert(1, ('Enqueue Series', 'XBMC.RunPlugin(%s)' % s1))

    else:
        if (args.mode is not None and
            args.mode in 'list_coll|list_series|queue'):

            if queued:
                cm.insert(1, ('Dequeue Series', 'XBMC.RunPlugin(%s)' % s2))
            else:
                cm.insert(1, ('Enqueue Series', 'XBMC.RunPlugin(%s)' % s1))

    cm.append(('Toggle debug', 'XBMC.ToggleDebug'))

    li.addContextMenuItems(cm, replaceItems=True)

    # Add item to list
    xbmcplugin.addDirectoryItem(handle     = int(sys.argv[1]),
                                url        = u,
                                listitem   = li,
                                isFolder   = isFolder,
                                totalItems = total_items)


def showMain(args):
    """Show main menu.

    """
    change_language = args._addon.getSetting("change_language")

    if crj.loadShelf(args) is False:
        addItem(args,
                {'Title': 'Session Failed: Check Login'})
        endofdirectory()
    else:
        if change_language != "0":
            crj.changeLocale()

        Anime   = args._lang(30100)
        Drama   = args._lang(30104)
        Queue   = args._lang(30105)
        History = args._lang(30111)

        addItem(args,
                {'Title':      Queue,
                 'mode':       'queue'})
        addItem(args,
                {'Title':      History,
                 'mode':       'History'})
        addItem(args,
                {'Title':      Anime,
                  'mode':       'Channels',
                  'media_type': 'Anime'})
        addItem(args,
                {'Title':      Drama,
                  'mode':       'Channels',
                  'media_type': 'Drama'})
        endofdirectory()


def channels(args):
    """Show Crunchyroll channels.

    """
    popular         = args._lang(30103)
    Simulcasts      = args._lang(30106)
    Recently_Added  = args._lang(30102)
    alpha           = args._lang(30112)
    Browse_by_Genre = args._lang(30107)
    seasons         = args._lang(30110)

    media_type      = args.media_type

    addItem(args,
            {'Title':      popular,
             'mode':       'list_series',
             'media_type': media_type,
             'filterx':    'popular',
             'offset':     '0'})
    addItem(args,
            {'Title':      Simulcasts,
             'mode':       'list_series',
             'media_type': media_type,
             'filterx':    'simulcast',
             'offset':     '0'})
    addItem(args,
            {'Title':      Recently_Added,
             'mode':       'list_series',
             'media_type': media_type,
             'filterx':    'updated',
             'offset':     '0'})
    addItem(args,
            {'Title':      alpha,
             'mode':       'list_series',
             'media_type': media_type,
             'filterx':    'alpha',
             'offset':     '0'})
    addItem(args,
            {'Title':      Browse_by_Genre,
             'mode':       'list_categories',
             'media_type': media_type,
             'filterx':    'genre',
             'offset':     '0'})
    addItem(args,
            {'Title':      seasons,
             'mode':       'list_categories',
             'media_type': media_type,
             'filterx':    'season',
             'offset':     '0'})
    endofdirectory()


def json_list_series(args):
    """List series.

    """
    crj.list_series(args)


def json_list_cat(args):
    """List categories.

    """
    crj.list_categories(args)


def json_list_collection(args):
    """List collections.

    """
    crj.list_collections(args)


def json_list_media(args):
    """List episodes.

    """
    crj.list_media(args)


def json_History(args):
    """Display Crunchyroll history.

    """
    crj.History(args)


def queue(args):
    """Display Crunchyroll queue.

    """
    crj.Queue(args)


def add_to_queue(args):
    """Add selected video series to queue at Crunchyroll.

    """
    crj.add_to_queue(args)


def remove_from_queue(args):
    """Remove selected video series from queue at Crunchyroll.

    """
    crj.remove_from_queue(args)


def startVideo(args):
    """Start video playback.

    """
    crj.startPlayback(args)


def Fail(args):
    """Unrecognized mode found.

    """
    badstuff = args._lang(30207)

    addItem(args,
            {'Title': badstuff,
             'mode':  'Fail'})

    log("CR: Main: checkMode fall through", xbmc.LOGWARNING)

    endofdirectory()


def parseArgs():
    """Decode arguments.

    """
    # Call updateArgs() with our formatted argv to create self.args object
    if (sys.argv[2]):
        exec("args = updateArgs(%s')"
             % (sys.argv[2][1:].replace('&', "',").replace('=', "='")))

        return args
    else:
        # updateArgs will turn the 'None' into None.
        # Don't simply define it as None because unquote_plus in updateArgs
        # will throw an exception.
        # This is a pretty ugly solution.
        return updateArgs(mode = 'None',
                          url  = 'None',
                          name = 'None')


def checkMode(args):
    """Run mode-specific functions.

    """
    mode = args.mode
    log("CR: Main: argv[0] = %s" % sys.argv[0])
    log("CR: Main: argv[1] = %s" % sys.argv[1])
    log("CR: Main: argv[2] = %s" % sys.argv[2])
    log("CR: Main: args = %s" % str(args.__dict__))
    log("CR: Main: mode = %s" % mode)

    if mode is None:
        showMain(args)
    elif mode == 'Channels':
        channels(args)
    elif mode == 'list_series':
        json_list_series(args)
    elif mode == 'list_categories':
        json_list_cat(args)
    elif mode == 'list_coll':
        json_list_collection(args)
    elif mode == 'list_media':
        json_list_media(args)
    elif mode == 'History':
        json_History(args)
    elif mode == 'queue':
        queue(args)
    elif mode == 'add_to_queue':
        add_to_queue(args)
    elif mode == 'remove_from_queue':
        remove_from_queue(args)
    elif mode == 'videoplay':
        startVideo(args)
    else:
        Fail(args)


def main():
    """Main function for the addon.

    """
    args = parseArgs()

    crj.loadShelf(args)

    xbmcplugin.setContent(int(sys.argv[1]), 'movies')

    checkMode(args)
