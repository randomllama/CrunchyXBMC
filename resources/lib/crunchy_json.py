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

import os
import re
import sys
import json
import gzip
import time
import random
import shelve
import socket
import string
import urllib
import httplib
import urllib2
import datetime
import StringIO
import cookielib

import xbmc
import xbmcgui
import xbmcplugin

import dateutil.tz
import dateutil.parser
import dateutil.relativedelta as durel

import crunchy_main as crm


__version__   = sys.modules["__main__"].__version__
__XBMCBUILD__ = xbmc.getInfoLabel("System.BuildVersion") + " " + sys.platform



class _Info(object):

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)



class CrunchyJSON(object):

    def __init__(self):
        self._addon = sys.modules['__main__'].__settings__
        self._lang  = sys.modules['__main__'].__language__

        self.loadShelf()


    def loadShelf(self):
        notice_msg     = self._lang(30200).encode("utf8")
        setup_msg      = self._lang(30203).encode("utf8")
        acc_type_error = self._lang(30312).encode("utf8")

        change_language = self._addon.getSetting("change_language")

        self.base_path = xbmc.translatePath(self._addon.getAddonInfo('profile')).decode('utf-8')

        self.base_cache_path = os.path.join(self.base_path, "cache")
        if not os.path.exists(self.base_cache_path):
            os.makedirs(self.base_cache_path)

        shelf_path = os.path.join(self.base_path, "cruchyXBMC")

        current_datetime = datetime.datetime.now(dateutil.tz.tzutc())

        try:
            # Load persistent vars
            userData = shelve.open(shelf_path, writeback=True)

            if change_language == "0":
                userData.setdefault('API_LOCALE',"enUS")
            elif change_language == "1":
                userData['API_LOCALE']  = "enUS"
            elif change_language == "2":
                userData['API_LOCALE']  = "enGB"
            elif change_language == "3":
                userData['API_LOCALE']  = "jaJP"
            elif change_language == "4":
                userData['API_LOCALE']  = "frFR"
            elif change_language == "5":
                userData['API_LOCALE']  = "deDE"
            elif change_language == "6":
                userData['API_LOCALE']  = "ptBR"
            elif change_language == "7":
                userData['API_LOCALE']  = "ptPT"
            elif change_language == "8":
                userData['API_LOCALE']  = "esLA"
            elif change_language == "9":
                userData['API_LOCALE']  = "esES"

            userData['username'] = self._addon.getSetting("crunchy_username")
            userData['password'] = self._addon.getSetting("crunchy_password")

            if 'device_id' not in userData:
                char_set  = string.ascii_letters + string.digits
                device_id = ''.join(random.sample(char_set, 32))
                userData["device_id"] = device_id
                log("CR: New device_id created. New device ID: "
                    + str(device_id))

            userData['API_HEADERS'] = [('User-Agent',      "Mozilla/5.0 (PLAYSTATION 3; 4.46)"),
                                       ('Host',            "api.crunchyroll.com"),
                                       ('Accept-Encoding', "gzip, deflate"),
                                       ('Accept',          "*/*"),
                                       ('Content-Type',    "application/x-www-form-urlencoded")]

            userData['API_URL']          = "https://api.crunchyroll.com"
            userData['API_VERSION']      = "1.0.1"
            userData['API_ACCESS_TOKEN'] = "S7zg3vKx6tRZ0Sf"
            userData['API_DEVICE_TYPE']  = "com.crunchyroll.ps3"

            userData.setdefault('premium_type', 'UNKNOWN')
            userData.setdefault('lastreported', (current_datetime -
                                                 durel.relativedelta(hours = +24)))
            self.userData = userData

        except:
            log("CR: Unexpected error:", sys.exc_info(), xbmc.LOGERROR)

            userData['session_id']      = ''
            userData['auth_expires']    = (current_datetime -
                                           durel.relativedelta(hours = +24))
            userData['lastreported']    = (current_datetime -
                                           durel.relativedelta(hours = +24))
            userData['premium_type']    = 'UNKNOWN'
            userData['auth_token']      = ''
            userData['session_expires'] = (current_datetime -
                                           durel.relativedelta(hours = +24))

            self.userData = userData
            userData.close()
            log("CR: Unable to load shelve")

            return False

        # Check to see if a session_id doesn't exist or if the current
        # auth token is invalid and if so start a new session and log it in
        if (('session_id' not in userData) or
            ('auth_expires' not in userData) or
            current_datetime > userData['auth_expires']):

            # Start new session
            log("CR: Starting new session")

            options = {'device_id':    userData['device_id'],
                       'device_type':  userData['API_DEVICE_TYPE'],
                       'access_token': userData['API_ACCESS_TOKEN']}

            request = self.makeAPIRequest('start_session', options)

            if request['error'] is False:
                userData['session_id']      = request['data']['session_id']
                userData['session_expires'] = (current_datetime +
                                               durel.relativedelta(hours = +4))
                userData['test_session']    = current_datetime

                log("CR: New session created!"
                    + " Session ID: " + str(userData['session_id']))

            elif request['error'] is True:
                log("CR: Error starting new session. Error message: "
                    + str(request['message']), xbmc.LOGERROR)

                return False

            # Login the session we just started
            if not userData['username'] or not userData['password']:
                log("CR: No username or password set")

                self.userData = userData
                userData.close()

                ex = 'XBMC.Notification("' + notice_msg + ':","' \
                     + setup_msg + '.", 3000)'
                xbmc.executebuiltin(ex)
                log("CR: No Crunchyroll account found!", xbmc.LOGERROR)

                return False

            else:
                log("CR: Login in the new session")

                options = {'password':   userData['password'],
                           'account':    userData['username']}

                request = self.makeAPIRequest('login', options)

                if request['error'] is False:
                    userData['auth_token']   = request['data']['auth']
                    userData['auth_expires'] = dateutil.parser.parse(request['data']['expires'])
                    userData['premium_type'] = ('free'
                                                    if request['data']['user']['premium'] == ''
                                                    else request['data']['user']['premium'])

                    log("CR: Login successful")

                elif request['error'] is True:
                    log("CR: Error logging in new session. Error message: "
                        + str(request['message']), xbmc.LOGERROR)

                    self.userData = userData
                    userData.close()
                    return False

            # Call for usage reporting
            if current_datetime > userData['lastreported']:
                userData['lastreported'] = (current_datetime +
                                            durel.relativedelta(hours = +24))
                self.userData = userData
                self.usage_reporting()

            # Verify user is premium
            if userData['premium_type'] in 'anime|drama|manga':
                log("CR: User is a premium " + str(userData['premium_type'])
                    + " member")

                self.userData = userData
                userData.close()
                return True

            else:
                log("CR: User is not a premium member")
                xbmc.executebuiltin('Notification(' + notice_msg + ',' +
                                    acc_type_error + ',5000)')

                self.userData = userData = None
                userData.close()

                crm.addItem(args,
                            {'Title': acc_type_error,
                             'mode':  'Fail'})
                crm.endofdirectory('none')

                return False

        # Check to see if a valid session and auth token exist and if so
        # reinitialize a new session using the auth token
        elif ('session_id' in userData and
              'auth_expires' in userData and
              current_datetime < userData['auth_expires'] and
              current_datetime > userData['session_expires']):

            # Re-start new session
            log("CR: Valid auth token was detected. Restarting session.")

            options = {'device_id':    userData["device_id"],
                       'device_type':  userData['API_DEVICE_TYPE'],
                       'access_token': userData['API_ACCESS_TOKEN'],
                       'auth':         userData['auth_token']}

            request = self.makeAPIRequest('start_session', options)

            if request['error'] is False:
                userData['session_id']      = request['data']['session_id']
                userData['auth_expires']    = dateutil.parser.parse(request['data']['expires'])
                userData['premium_type']    = ('free'
                                                   if request['data']['user']['premium'] == ''
                                                   else request['data']['user']['premium'])
                userData['auth_token']      = request['data']['auth']
                # 4 hours is a guess. Might be +/- 4.
                userData['session_expires'] = (current_datetime +
                                               durel.relativedelta(hours = +4))
                userData['test_session']    = current_datetime

                log("CR: Session restart successful. Session ID: "
                    + str(userData['session_id']))

                # Call for usage reporting
                if current_datetime > userData['lastreported']:
                    userData['lastreported'] = (current_datetime +
                                                durel.relativedelta(hours = +24))
                    self.userData = userData
                    self.usage_reporting()

                # Verify user is premium
                if userData['premium_type'] in 'anime|drama|manga':
                    log("CR: User is a premium "
                        + str(userData['premium_type']) + " member")

                    self.userData = userData
                    userData.close()

                    return True

                else:
                    log("CR: User is not a premium member")
                    xbmc.executebuiltin('Notification(' + notice_msg + ','
                                        + acc_type_error + ',5000)')

                    self.userData = userData = None
                    userData.close()

                    crm.addItem(args,
                                {'Title': acc_type_error,
                                 'mode':  'Fail'})
                    crm.endofdirectory('none')

                    return False

            elif request['error'] is True:
                # Remove userData so a new session is started next time
                del userData['session_id']
                del userData['auth_expires']
                del userData['premium_type']
                del userData['auth_token']
                del userData['session_expires']

                log("CR: Error restarting session. Error message: "
                    + str(request['message']), xbmc.LOGERROR)

                self.userData = userData
                userData.Save()
                return False

        # If we got to this point that means a session exists and it's still
        # valid, we don't need to do anything
        elif ('session_id' in userData and
              current_datetime < userData['session_expires']):

            # This section below is stupid slow
            #return True
            if (userData['test_session'] is None or
                current_datetime > userData['test_session']):

                # Test once every 10 min
                userData['test_session'] = (current_datetime +
                                            durel.relativedelta(minutes = +10))

                # Test to make sure the session still works
                # (sometimes sessions just stop working)
                fields  = "".join(["media.episode_number,",
                                   "media.name,",
                                   "media.description,",
                                   "media.media_type,",
                                   "media.series_name,",
                                   "media.available,",
                                   "media.available_time,",
                                   "media.free_available,",
                                   "media.free_available_time,",
                                   "media.duration,",
                                   "media.url,",
                                   "media.screenshot_image,",
                                   "image.fwide_url,",
                                   "image.fwidestar_url,",
                                   "series.landscape_image,",
                                   "image.full_url"])
                options = {'media_types': "anime|drama",
                           'fields':      fields}
                request = self.makeAPIRequest('queue', options)

                if request['error'] is False:
                    log("CR: A valid session was detected."
                        + " Using existing session ID: "
                        + str(userData['session_id']))

                    # Call for usage reporting
                    if current_datetime > userData['lastreported']:
                        userData['lastreported'] = (current_datetime +
                                                    durel.relativedelta(hours = +24))
                        self.userData = userData
                        self.usage_reporting()

                    # Verify user is premium
                    if userData['premium_type'] in 'anime|drama|manga':
                        log("CR: User is a premium "
                            + str(userData['premium_type']) + " member")

                        self.userData = userData
                        userData.close()
                        return True

                    else:
                        log("CR: User is not a premium member")
                        xbmc.executebuiltin('Notification(' + notice_msg + ','
                                            + acc_type_error + ',5000)')

                        self.userData = userData = None
                        userData.close()

                        crm.UI().addItem({'Title': acc_type_error,
                                          'mode':  'Fail'})
                        crm.UI().endofdirectory('none')

                        return False

                elif request['error'] is True:
                    log("CR: Something in the login process went wrong!")

                    del userData['session_id']
                    del userData['auth_expires']
                    del userData['premium_type']
                    del userData['auth_token']
                    del userData['session_expires']

                    self.userData = userData
                    userData.close()
                    return False

        # This is here as a catch all in case something gets messed up along
        # the way. Remove userData variables so we start a new session
        # next time around.
        else:
            del userData['session_id']
            del userData['auth_expires']
            del userData['premium_type']
            del userData['auth_token']
            del userData['session_expires']

            log("CR: Something in the login process went wrong!")

            self.userData = userData
            userData.close()
            return False


    def list_series(self, args):
        fields  = "".join(["series.name,",
                           "series.description,",
                           "series.series_id,",
                           "series.rating,",
                           "series.media_count,",
                           "series.url,",
                           "series.publisher_name,",
                           "series.year,",
                           "series.portrait_image,",
                           "image.large_url,",
                           "series.landscape_image,",
                           "image.full_url"])
        options = {'media_type': args.media_type.lower(),
                   'filter':     args.filterx,
                   'fields':     fields,
                   'limit':      '64',
                   'offset':     int(args.offset)}

        request = self.makeAPIRequest('list_series', options)

        queue   = self.get_queued()

        if request['error'] is False:
            counter = 0
            for series in request['data']:
                counter = counter + 1

                # Only available on some series
                year        = ('None'
                                   if series['year'] is None
                                   else series['year'])
                description = (''
                                   if series['description'] is None
                                   else series['description'].encode('utf-8'))
                thumb       = (''
                                   if (series['portrait_image'] is None or
                                      series['portrait_image']['large_url'] is None or
                                      'portrait_image' not in series or
                                      'large_url' not in series['portrait_image'])
                                   else series['portrait_image']['full_url'])
                art         = (''
                                   if (series['landscape_image'] is None or
                                      series['landscape_image']['full_url'] is None or
                                      'landscape_image' not in series or
                                      'full_url' not in series['landscape_image'])
                                   else series['landscape_image']['full_url'])
                rating      = ('0'
                                   if (series['rating'] == '' or
                                       'rating' not in series)
                                   else series['rating'])

                # Crunchyroll seems to like passing series
                # without these things
                if ('media_count' in series and
                    'series_id' in series and
                    'name' in series and
                    series['media_count'] > 0):

                    queued = (series['series_id'] in queue)

                    crm.addItem(args,
                                {'Title':        series['name'].encode("utf8"),
                                 'mode':         'list_coll',
                                 'series_id':    series['series_id'],
                                 'count':        str(series['media_count']),
                                 'Thumb':        thumb,
                                 'Fanart_Image': art,
                                 'plot':         description,
                                 'year':         year},
                                isFolder=True,
                                queued=queued)

            if counter >= 64:
                offset = str(int(args.offset) + counter)
                crm.addItem(args,
                            {'Title':      '...load more',
                             'mode':       'list_series',
                             'media_type': args.media_type,
                             'filterx':    args.filterx,
                             'offset':     offset})

        crm.endofdirectory('none')


    def list_categories(self, args):
        options = {'media_type': args.media_type.lower()}

        request = self.makeAPIRequest('categories', options)

        if request['error'] is False:
            for i in request['data'][args.filterx]:
                crm.addItem(args,
                            {'Title':      i['label'].encode("utf8"),
                             'mode':       'list_series',
                             'media_type': args.media_type,
                             'filterx':    'tag:' + i['tag']},
                            isFolder=True)

        crm.endofdirectory('none')


    def list_collections(self, args):
        fields  = "".join(["collection.collection_id,",
                           "collection.season,",
                           "collection.name,",
                           "collection.description,",
                           "collection.complete,",
                           "collection.media_count"])
        options = {'series_id': args.series_id,
                   'fields':    fields,
                   'sort':      'desc',
                   'limit':     args.count}

        request = self.makeAPIRequest('list_collections', options)

        if request['error'] is False:
            if len(request['data']) <= 1:
                for collection in request['data']:
                    args.complete = '1' if collection['complete'] else '0'
                    args.id       = collection['collection_id']

                    return self.list_media(args)
            else:
                queued = (args.series_id in self.get_queued())

                for collection in request['data']:
                    complete = '1' if collection['complete'] else '0'
                    crm.addItem(args,
                                {'Title':        collection['name'].encode("utf8"),
                                 'filterx':      args.name,
                                 'mode':         'list_media',
                                 'count':        str(args.count),
                                 'id':           collection['collection_id'],
                                 'plot':         collection['description'].encode("utf8"),
                                 'complete':     complete,
                                 'season':       str(collection['season']),
                                 'series_id':    args.series_id,
                                 'Thumb':        args.icon,
                                 'Fanart_Image': args.fanart},
                                isFolder=True,
                                queued=queued)

        crm.endofdirectory('none')


    def list_media(self, args):
        sort    = 'asc' if args.complete is '1' else 'desc'
        fields  = "".join(["media.episode_number,",
                           "media.name,",
                           "media.description,",
                           "media.media_type,",
                           "media.series_name,",
                           "media.available,",
                           "media.available_time,",
                           "media.free_available,",
                           "media.free_available_time,",
                           "media.playhead,",
                           "media.duration,",
                           "media.url,",
                           "media.screenshot_image,",
                           "image.fwide_url,",
                           "image.fwidestar_url,",
                           "series.landscape_image,",
                           "image.full_url"])
        options = {'collection_id': args.id,
                   'fields':        fields,
                   'sort':          sort,
                   'limit':         '256'}

        request = self.makeAPIRequest('list_media', options)

        if request['error'] is False:
            return self.list_media_items(args,
                                         request['data'],
                                         args.name,
                                         args.season,
                                         'normal',
                                         args.fanart)


    def list_media_items(self, args, request, series_name, season, mode, fanart):
        """List video episodes.

        """
        queue = self.get_queued()

        for media in request:
            queued = ((media['series']['series_id']
                           if mode == "history"
                           else args.series_id) in queue)

            # The following are items to help display Recently Watched
            # and Queue items correctly
            season      = (media['collection']['season']
                               if mode == "history"
                               else season)
            series_name = (media['series']['name']
                               if mode == "history"
                               else series_name)
            series_name = (media['most_likely_media']['series_name']
                               if mode == "queue"
                               else series_name)
            # On history/queue, the fanart is obtained directly from the json
            fanart      = (media['series']['landscape_image']['fwide_url']
                               if (mode == "history" or mode == "queue")
                               else fanart)
            # History media is one level deeper in the json string
            # than normal media items
            media       = (media['media']
                               if mode == "history"
                               else media)

            # Some queue items don't have most_likely_media, skip them
            if mode == "queue" and 'most_likely_media' not in media:
                continue

            # Queue media is one level deeper in the json string
            # than normal media items
            media = media['most_likely_media'] if mode == "queue" else media

            current_datetime   = datetime.datetime.now(dateutil.tz.tzutc())
            available_datetime = dateutil.parser.parse(media['available_time'])
            available_datetime = available_datetime.astimezone(dateutil.tz.tzlocal())
            available_date     = available_datetime.date()
            available_delta    = available_datetime - current_datetime
            available_in       = (str(available_delta.days) + " days."
                                      if available_delta.days > 0
                                      else str(available_delta.seconds/60/60)
                                          + " hours.")

            # Fix Crunchyroll inconsistencies & add details for upcoming or
            # unreleased episodes.
            # PV episodes have no episode number so we set it to 0.
            media['episode_number'] = ('0'
                                           if media['episode_number'] == ''
                                           else media['episode_number'])
            # CR puts letters into some rare episode numbers
            media['episode_number'] = re.sub('\D', '', media['episode_number'])

            if media['episode_number'] == '0':
                name = ("NO NAME"
                            if media['name'] == ''
                            else media['name'])
            else:
                # CR doesn't seem to include episode names for all media,
                # make one up
                name = ("Episode " + str(media['episode_number'])
                            if media['name'] == ''
                            else "Episode " + media['episode_number'] + " - "
                                + media['name'])

            name = (series_name + " " + name
                        if (mode == "history" or
                            mode == "queue")
                        else name)
            name = ("* " + name
                        if media['free_available'] is False
                        else name)
            soon = ("Coming Soon - " + series_name
                    + " Episode " + str(media['episode_number'])
                        if mode == "queue"
                        else "Coming Soon - Episode "
                            + str(media['episode_number']))
            # Set the name for upcoming episode
            name = soon if media['available'] is False else name

            # There is a bug which prevents Season 0 from displaying correctly
            # in PMC. This is to help fix that. Will break if a series has
            # both season 0 and 1.
            #season = '1' if season == '0' else season

            # Not all shows have thumbnails
            thumb = ("http://static.ak.crunchyroll.com/i/no_image_beta_full.jpg"
                         if media['screenshot_image'] is None
                         else media['screenshot_image']['fwide_url']
                             if media['free_available'] is True
                             else media['screenshot_image']['fwidestar_url'])
            # Sets the thumbnail to coming soon if the episode
            # isn't available yet
            thumb = ("http://static.ak.crunchyroll.com/i/coming_soon_beta_fwide.jpg"
                         if media['available'] is False
                         else thumb)

            description = (''
                               if media['description'] is None
                               else media['description'].encode('utf-8'))
            # Set the description for upcoming episodes
            description = ("This episode will be available in "
                           + str(available_in)
                               if media['available'] is False
                               else description)

            duration = ("0"
                            if media['available'] is False
                            else str(media['duration']))
            # Current playback point
            playhead = ("0"
                            if media['available'] is False
                            else str(media['playhead']))

            # Adding published date instead
            year = ('None'
                        if media['available_time'] is None
                        else media['available_time'][:10])

            url = media['url']
            media_id = url.split('-')[-1]

            crm.addItem(args,
                        {'Title':        name.encode("utf8"),
                         'mode':         'videoplay',
                         'id':           media_id.encode("utf8"),
                         'Thumb':        thumb.encode("utf8"),
                         'url':          url.encode("utf8"),
                         'Fanart_Image': fanart,
                         'plot':         description,
                         'year':         year,
                         'playhead':     playhead,
                         'duration':     duration},
                        isFolder=False,
                        queued=queued)

        crm.endofdirectory('none')


    def History(self, args):
        fields  = "".join(["media.episode_number,",
                           "media.name,",
                           "media.description,",
                           "media.media_type,",
                           "media.series_name,",
                           "media.available,",
                           "media.available_time,",
                           "media.free_available,",
                           "media.free_available_time,",
                           "media.duration,",
                           "media.playhead,",
                           "media.url,",
                           "media.screenshot_image,",
                           "image.fwide_url,",
                           "image.fwidestar_url"])
        options = {'media_types': "anime|drama",
                   'fields':      fields,
                   'limit':       '256'}

        request = self.makeAPIRequest('recently_watched', options)

        if request['error'] is False:
            return self.list_media_items(args,
                                         request['data'],
                                         'Recently Watched',
                                         '1',
                                         'history',
                                         'fanart')


    def Queue(self, args):
        queue_type = self._addon.getSetting("queue_type")

        log("CR: Queue: queue type is " + str(queue_type))
        if queue_type == '0':
            fields  = "".join(["media.episode_number,",
                               "media.name,",
                               "media.description,",
                               "media.media_type,",
                               "media.series_name,",
                               "media.available,",
                               "media.available_time,",
                               "media.free_available,",
                               "media.free_available_time,",
                               "media.duration,",
                               "media.playhead,",
                               "media.url,",
                               "media.screenshot_image,",
                               "image.fwide_url,",
                               "image.fwidestar_url,",
                               "series.landscape_image,",
                               "image.full_url"])
            options = {'media_types': "anime|drama",
                       'fields':      fields}

            request = self.makeAPIRequest('queue', options)

            log("CR: Queue: request['error'] = " + str(request['error']))
            if request['error'] is False:
                return self.list_media_items(args,
                                             request['data'],
                                             'Queue',
                                             '1',
                                             'queue',
                                             'fanart')

        elif queue_type == '1':
            fields  = "".join(["series.name,",
                               "series.description,",
                               "series.series_id,",
                               "series.rating,",
                               "series.media_count,",
                               "series.url,",
                               "series.publisher_name,",
                               "series.year,",
                               "series.portrait_image,",
                               "image.large_url,",
                               "series.landscape_image,",
                               "image.full_url"])
            options = {'media_types': "anime|drama",
                       'fields':      fields}

            request = self.makeAPIRequest('queue', options)

            log("CR: Queue: request['error'] = " + str(request['error']))
            if request['error'] is False:
                log("CR: Queue: has %d series" % len(request['data']))
                for series in request['data']:
                    series      = series['series']
                    # Only available for some series
                    year        = ('None'
                                       if series['year'] is None
                                       else series['year'])
                    description = (''
                                       if series['description'] is None
                                       else series['description'].encode('utf-8'))

                    thumb  = (''
                                  if (series['portrait_image'] is None or
                                      series['portrait_image']['large_url'] is None or
                                      'portrait_image' not in series or
                                      'large_url' not in series['portrait_image'])
                                  else series['portrait_image']['full_url'])
                    art    = ('' if (series['landscape_image'] is None or
                                     series['landscape_image']['full_url'] is None or
                                     'landscape_image' not in series or
                                     'full_url' not in series['landscape_image'])
                                  else series['landscape_image']['full_url'])
                    rating = ('0' if (series['rating'] == '' or
                                      'rating' not in series)
                                  else series['rating'])

                    # Crunchyroll seems to like passing series
                    # without these things
                    if ('media_count' in series and
                        'series_id' in series and
                        'name' in series and
                        series['media_count'] > 0):

                        crm.addItem(args,
                                    {'Title':        series['name'].encode("utf8"),
                                     'mode':         'list_coll',
                                     'series_id':    series['series_id'],
                                     'Thumb':        thumb,
                                     'Fanart_Image': art,
                                     'plot':         description,
                                     'year':         year},
                                    isFolder=True,
                                    queued=True)

                        log("CR: Queue: series = '%s' queued"
                            % series['name'.encode('utf8')])
                    else:
                        log("CR: Queue: series not queued!")

                crm.endofdirectory('none')


    def get_queued(self):
        """Get list of queued series.

        """
        options = {'fields': "series.series_id"}

        request = self.makeAPIRequest('queue', options)

        return [col['series']['series_id']
                    for col in request['data']]


    def add_to_queue(self, args):
        """Add selected video series to queue at Crunchyroll.

        """
        # Get series_id
        if args.series_id is None:
            options = {'media_id': args.id,
                       'fields':   "series.series_id"}
            request = self.makeAPIRequest('info', options)

            series_id = request['data']['series_id']
        else:
            series_id = args.series_id

        # Add the series to queue at CR if it is not there already
        options = {'series_id': series_id,
                   'fields':    "series.series_id"}
        request = self.makeAPIRequest('queue', options)

        for col in request['data']:
            if series_id == col['series']['series_id']:
                return

        options = {'series_id': series_id}

        request = self.makeAPIRequest('add_to_queue', options)

        log("CR: add_to_queue: request['error'] = " + str(request['error']))


    def remove_from_queue(self, args):
        """Remove selected video series from queue at Crunchyroll.

        """
        # Get series_id
        if args.series_id is None:
            options = {'media_id': args.id,
                       'fields':   "series.series_id"}
            request = self.makeAPIRequest('info', options)

            series_id = request['data']['series_id']
        else:
            series_id = args.series_id

        # Remove the series from queue at CR if it is there
        options = {'series_id': series_id,
                   'fields':    "series.series_id"}
        request = self.makeAPIRequest('queue', options)

        for col in request['data']:
            if series_id == col['series']['series_id']:
                options = {'series_id': series_id}

                request = self.makeAPIRequest('remove_from_queue', options)

                log("CR: remove_from_queue: request['error'] = "
                    + str(request['error']))

        # Refresh directory listing
        xbmc.executebuiltin('XBMC.Container.Refresh')


    def startPlayback(self, args):
        """Play video stream with selected quality.

        """
        res_quality = ['low', 'mid', 'high', 'ultra']
        quality     = res_quality[int(self._addon.getSetting("video_quality"))]

        fields = "".join(["media.episode_number,",
                          "media.name,",
                          "media.playhead,",
                          "media.description,",
                          "media.url,",
                          "media.stream_data"])

        values = {'media_id': args.id,
                  'fields':   fields}

        request = self.makeAPIRequest('info', values)

        if request['error']:
            log("CR: startPlayback: Connection failed, aborting..")
            sys.exit(1)

        if self._addon.getSetting("playback_resume") == 'true':
            playback_resume = True
        else:
            playback_resume = False

        if playback_resume is not True:
            resumetime = "0"
        else:
            resumetime = str(request['data']['playhead'])

        if int(resumetime) > 0:
            playcount = 0
        else:
            playcount = 1

        allurl = {}
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

        if request['error'] is False:
            if request['data']['stream_data'] is not None:
                for stream in request['data']['stream_data']['streams']:
                    allurl[stream['quality']] = stream['url']

                if allurl[quality] is not None:
                    url = allurl[quality]
                elif quality == 'ultra' and allurl['high'] is not None:
                    url = allurl['high']
                elif allurl['mid'] is not None:
                    url = allurl['mid']
                else:
                    url = allurl['low']

                item = xbmcgui.ListItem(args.name, path=url)
                item.setInfo(type="Video", infoLabels={"Title":     args.name,
                                                       "playcount": playcount})
                item.setThumbnailImage(args.icon)
                item.setProperty('TotalTime',  args.duration)
                item.setProperty('ResumeTime', resumetime)

                log("CR: startPlayback: url = %s" % url)
                player = xbmc.Player()

                xbmcplugin.setResolvedUrl(int(sys.argv[1]),
                                          succeeded=True,
                                          listitem=item)

                log("CR: startPlayback: Starting ...")

                timeplayed = resumetime

                # Give the player time to start up
                time.sleep(3)

                s = "CR: startPlayback: player is playing == %d"
                log(s % player.isPlaying(), xbmc.LOGDEBUG)

                playlist_position = playlist.getposition()

                if int(resumetime) <= 60:
                    playback_resume = False

                try:
                    if playback_resume is True:
                        player.seekTime(float(resumetime))

                    while playlist_position == playlist.getposition():
                        timeplayed = str(int(player.getTime()))

                        values = {'event':      'playback_status',
                                  'media_id':   args.id,
                                  'playhead':   timeplayed}

                        request = self.makeAPIRequest('log', values)

                        # Use video timeline here
                        xbmc.sleep(5000)

                except RuntimeError as e:
                    log("CR: startPlayback: Player stopped playing: %r" % e)

                log("CR: startPlayback: Finished logging: %s" % url)


    def pretty(self, d, indent=1):
        """Pretty printer for dictionaries.

        """
        if isinstance(d, list):
            for i in d:
                log('--', xbmc.LOGDEBUG)
                self.pretty(i, indent + 1)
        else:
            for key, value in d.iteritems():
                log(' ' * 2 * indent + str(key), xbmc.LOGDEBUG)
                if isinstance(value, (dict, list)):
                    self.pretty(value, indent + 1)
                else:
                    if isinstance(value, unicode):
                        value = value.encode('utf8')
                    else:
                        value = str(value)
                    log(' ' * 2 * (indent + 1) + value, xbmc.LOGDEBUG)


    def makeAPIRequest(self, method, options):
        if self.userData['premium_type'] in 'anime|drama|manga|UNKNOWN':
            log("CR: makeAPIRequest: get JSON")

            values = {'version':    self.userData['API_VERSION'],
                      'locale':     self.userData['API_LOCALE']}

            if method != 'start_session':
                values['session_id'] = self.userData['session_id']

            values.update(options)
            options = urllib.urlencode(values)

            opener = urllib2.build_opener()
            opener.addheaders = self.userData['API_HEADERS']
            urllib2.install_opener(opener)

            url = self.userData['API_URL'] + "/" + method + ".0.json"

            log("CR: makeAPIRequest: url = %s" % url)
            log("CR: makeAPIRequest: options = %s" % options)


            try:
                en = ev = None

                req = opener.open(url, options)
                json_data = req.read()

                if req.headers.get('content-encoding', None) == 'gzip':
                    json_data = gzip.GzipFile(fileobj=StringIO.StringIO(json_data))
                    json_data = json_data.read().decode('utf-8', 'ignore')

                req.close()

                request = json.loads(json_data)

            except (httplib.BadStatusLine,
                    socket.error,
                    urllib2.HTTPError,
                    urllib2.URLError) as e:

                log("CR: makeAPIRequest: Connection failed: %r" % e,
                    xbmc.LOGERROR)

                en, ev = sys.exc_info()[:2]
            finally:
                # Return dummy response if connection failed
                if en is not None:
                    request = {'code':    'error',
                               'message': "Connection failed: %r, %r" % (en, ev),
                               'error':   True}

            #log("CR: makeAPIRequest: request = %s" % str(request), xbmc.LOGDEBUG)
            log("CR: makeAPIRequest: reply =", xbmc.LOGDEBUG)
            self.pretty(request)

        else:
            pt = self.userData['premium_type']
            s  = "Premium type check failed, premium_type:"

            request = {'code':    'error',
                       'message': "%s %s" % (s, pt),
                       'error':   True}

            log("CR: makeAPIRequest: %s %s" % (s, pt), xbmc.LOGERROR)

        return request


    def changeLocale(self):
        cj           = cookielib.LWPCookieJar()

        notice      = self._lang(30200).encode("utf8")
        notice_msg  = self._lang(30211).encode("utf8")
        notice_err  = self._lang(30206).encode("utf8")
        notice_done = self._lang(30310).encode("utf8")

        icon = xbmc.translatePath(self._addon.getAddonInfo('icon'))

        ua = 'Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0'

        if (self.userData['username'] != '' and
            self.userData['password'] != ''):

            log("CR: Attempting to log-in with your user account...")
            xbmc.executebuiltin('Notification(' + notice + ','
                                + notice_msg + ',5000,' + icon + ')')

            url  = 'https://www.crunchyroll.com/?a=formhandler'
            data = urllib.urlencode({'formname': 'RpcApiUser_Login',
                                     'next_url': '',
                                     'fail_url': '/login',
                                     'name':     self.userData['username'],
                                     'password': self.userData['password']})
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            opener.addheaders = [('Referer',    'https://www.crunchyroll.com'),
                                 ('User-Agent', ua)]
            urllib2.install_opener(opener)
            req = opener.open(url, data)
            req.close()

        else:
            xbmc.executebuiltin('Notification(' + notice + ','
                                + notice_err + ',5000,' + icon + ')')
            log("CR: No Crunchyroll account found!")

        url  = 'https://www.crunchyroll.com/?a=formhandler'
        data = urllib.urlencode({'next_url': '',
                                 'language': self.userData['API_LOCALE'],
                                 'formname': 'RpcApiUser_UpdateDefaultSoftSubLanguage'})
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.addheaders = [('Referer',    'https://www.crunchyroll.com/acct/?action=video'),
                             ('User-Agent', ua)]
        self.opener = opener
        urllib2.install_opener(opener)

        # Enter in the video settings page first (doesn't work without it)
        req = self.opener.open("https://www.crunchyroll.com/acct/?action=video")

        # Now do the actual language change
        req = self.opener.open(url, data)
        req.close()

        log('CR: Now using ' + self.userData['API_LOCALE'])
        xbmc.executebuiltin('Notification(' + notice + ','
                            + notice_done + ',5000,' + icon + ')')
        log("CR: Disabling the force change language setting")

        self._addon.setSetting(id="change_language", value="0")


    def usage_reporting(self):
        log("CR: Attempting to report usage")

        url  = ''.join(['https://docs.google.com/forms/d',
                        '/1_qB4UznRfx69JrGCYmKbbeQcFc_t2-9fuNvXGGvl8mk',
                        '/formResponse'])
        data = urllib.urlencode({'entry_1580743010': self.userData['device_id'],
                                 'entry_623948459':  self.userData['premium_type'],
                                 'entry_1130326797': __version__,
                                 'entry.590894822':  __XBMCBUILD__})

        ua = 'Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0'

        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', ua)]
        urllib2.install_opener(opener)

        req = opener.open(url, data)
        req.close()



def log(msg,
        level=xbmc.LOGNOTICE,
        rex=re.compile(r'((?<=password=)[^&]*|(?<=account=)[^&]*)')):
    """XBMC log with matched regex blanked out.

    By default blank out user account name and password.
    """
    xbmc.log(re.sub(rex, "********", msg), level)
