# -*- coding: utf-8 -*-
"""
    tipfy.ext.auth.facebook
    ~~~~~~~~~~~~~~~~~~~~~~~

    Implementation of Facebook authentication scheme.

    Ported from `tornado.auth <http://github.com/facebook/tornado/blob/master/tornado/auth.py>`_.

    :copyright: 2009 Facebook.
    :copyright: 2010 tipfy.org.
    :license: Apache License Version 2.0, see LICENSE.txt for more details.
"""
from __future__ import absolute_import
import functools
import hashlib
import logging
import time
import urlparse
import urllib
import datetime
import facebookAPI

from google.appengine.api import urlfetch

from django.utils import simplejson

from tipfy import redirect, REQUIRED_VALUE

#: Default configuration values for this module. Keys are:
#:
#: - ``api_key``: Key provided when you register an application with
#:   Facebook.
#: - ``app_secret``: Secret provided when you register an application
#:   with Facebook.
default_config = {
    'api_key':    REQUIRED_VALUE,
    'app_secret': REQUIRED_VALUE,
}


class FacebookServerFlowMixin(object):
    """A :class:`tipfy.RequestHandler` mixin that implements Facebook Connect
    authentication.

    To authenticate with Facebook, register your application with
    Facebook at http://www.facebook.com/developers/apps.php. Then
    copy your API Key and Application Secret to config.py:

    <<code python>>
    config['tipfy.ext.auth.twitter'] = {
        'api_key':    'XXXXXXXXXXXXXXX',
        'app_secret': 'XXXXXXXXXXXXXXX',
    }
    <</code>>

    When your application is set up, you can use the FacebookMixin like this
    to authenticate the user with Facebook:

    <<code python>>
    from tipfy import RequestHandler, abort
    from tipfy.ext.auth.facebook import FacebookMixin

    class FacebookHandler(RequestHandler, FacebookMixin):
        def get(self):
            if self.request.args.get('session', None):
                return self.get_authenticated_user(self._on_auth)

            return self.authenticate_redirect()

        def _on_auth(self, user):
            if not user:
                abort(403)

            # Set the user in the session.
    <</code>>

    The user object returned by get_authenticated_user() includes the
    attributes 'facebook_uid' and 'name' in addition to session attributes
    like 'session_key'. You should save the session key with the user; it is
    required to make requests on behalf of the user later with
    facebook_request().
    """
    @property
    def _facebook_app_id(self):
        return self.app.get_config('tipfy.ext.auth.facebook', 'app_id')

    @property
    def _facebook_api_key(self):
        return self.app.get_config('tipfy.ext.auth.facebook', 'api_key')

    @property
    def _facebook_secret(self):
        return self.app.get_config('tipfy.ext.auth.facebook', 'app_secret')

    def authenticate_redirect(self, callback_uri=None, cancel_uri=None,
                              extended_permissions=None):
        """Authenticates/installs this app for the current user."""
        callback_uri = callback_uri or self.request.path
        args = {
            'client_id':        self._facebook_app_id,
            'redirect_uri': urlparse.urljoin(self.request.url, callback_uri),
        }

        if extended_permissions:
            if isinstance(extended_permissions, basestring):
                extended_permissions = [extended_permissions]

            args['scope'] = ','.join(extended_permissions)
        
        redirect_url = 'https://www.facebook.com/dialog/oauth?' + urllib.urlencode(args)
        return redirect(redirect_url)
        #return redirect('http://www.facebook.com/login.php?' +
        #                urllib.urlencode(args))
        
    def authorize_redirect(self, extended_permissions, callback_uri=None,
                           cancel_uri=None):
        """Redirects to an authorization request for the given FB resource.

        The available resource names are listed at
        http://wiki.developers.facebook.com/index.php/Extended_permission.
        The most common resource types include:

            publish_stream
            read_stream
            email
            sms

        extended_permissions can be a single permission name or a list of
        names. To get the session secret and session key, call
        get_authenticated_user() just as you would with
        authenticate_redirect().
        """
        return self.authenticate_redirect(callback_uri, cancel_uri,
                                          extended_permissions)

    def get_authenticated_user(self, callback):
        """Fetches the authenticated Facebook user.

        The authenticated user includes the special Facebook attributes
        'session_key' and 'facebook_uid' in addition to the standard
        user attributes like 'name'.
        """
        
        code = self.request.args.get('code')
        #callback_uri = callback_uri or self.request.path
        args = {
            'client_id':        self._facebook_app_id,
            'redirect_uri': self.request.base_url, #http://local-treasure-raider.com:8080/auth/facebookserverflow', #http%3A%2F%2Flocal-treasure-raider.com%3A8080%2Fauth%2Ffacebookserverflow
            'client_secret' : self._facebook_secret,
            'code' : code
        }

        url = 'https://graph.facebook.com/oauth/access_token?' + urllib.urlencode(args)
        try:
            response = urlfetch.fetch(url, deadline=10)
        except urlfetch.DownloadError, e:
            logging.exception(e)
            return callback(None)

        logging.info('result from access token call: ' + response.content)
        nvPairs = response.content.split('&')
        data = {}
        for pair in nvPairs:
            logging.info('pair: ' + pair)
            parts = pair.split('=')
            key = parts[0]
            value = parts[1]
            data[key] = value
            
        access_token = data['access_token']
        expires_seconds = data['expires']
        #access_token='150520701677303|2.G0_tmX4BgIBa4JUd6VUkiA__.3600.1301968800-1180287650|AR8CU0swRp3ra2TEaOXRv1aukhc'
        graph = facebookAPI.GraphAPI(access_token)
        try:
            profile = graph.get_object("me")
        except Exception, e:
            logging.error(e)

        #friends = graph.get_connections("me", "friends")
        #profile['friend_ids'] = ','.join(['facebook|' + friend['id'] for friend in friends['data']])

        profile['uid'] = profile['id']
        profile['access_token'] = access_token
        profile['expires_seconds'] = expires_seconds
        profile['token_acquired_time'] = str(datetime.datetime.now())
        return callback(profile)

    def facebook_request(self, method, callback, **kwargs):
        """Makes a Facebook API REST request.

        We automatically include the Facebook API key and signature, but

        it is the callers responsibility to include 'session_key' and any

        The available Facebook methods are documented here:
        http://wiki.developers.facebook.com/index.php/API

        Here is an example for the stream.get() method:

        from tipfy import RequestHandler, redirect
        from tipfy.ext.auth.facebook import FacebookMixin
        from tipfy.ext.jinja2 import Jinja2Mixin

        class MainHandler(RequestHandler, Jinja2Mixin, FacebookMixin):
            def get(self):
                self.facebook_request(
                    method='stream.get',
                    callback=self._on_stream,
                    session_key=self.current_user['session_key'])

            def _on_stream(self, stream):
                if stream is None:
                   # Not authorized to read the stream yet?
                   return redirect(self.authorize_redirect('read_stream'))

                return self.render_response('stream.html', stream=stream)

        """
        if not method.startswith('facebook.'):
            method = 'facebook.' + method

        kwargs.update({
            'api_key': self._facebook_api_key,
            'v':       '1.0',
            'method':  method,
            'call_id': str(long(time.time() * 1e6)),
            'format':  'json',
        })

        kwargs['sig'] = self._signature(kwargs)
        url = 'http://api.facebook.com/restserver.php?' + \
            urllib.urlencode(kwargs)

        try:
            response = urlfetch.fetch(url, deadline=10)
            return self._parse_response(callback, response)
        except urlfetch.DownloadError, e:
            logging.exception(e)

        return self._parse_response(callback, None)

    def _on_get_user_info(self, callback, session, users):
        if users is None:
            return callback(None)

        user = users[0]
        return callback({
            'name':            user['name'],
            'first_name':      user['first_name'],
            'last_name':       user['last_name'],
            'uid':             user['uid'],
            'locale':          user['locale'],
            'pic_square':      user['pic_square'],
            'profile_url':     user['profile_url'],
            'username':        user.get('username'),
            'session_key':     session['session_key'],
            'session_expires': session.get('expires'),
        })

    def _parse_response(self, callback, response):
        if not response:
            logging.warning('Missing Facebook response.')
            return callback(None)
        elif response.status_code < 200 or response.status_code >= 300:
            logging.warning('HTTP error from Facebook (%d): %s',
                response.status_code, response.content)
            return callback(None)

        try:
            json = simplejson.loads(response.content)
        except:
            logging.warning('Invalid JSON from Facebook: %r', response.content)
            return callback(None)

        if isinstance(json, dict) and json.get('error_code'):
            logging.warning('Facebook error: %d: %r', json['error_code'],
                            json.get('error_msg'))
            return callback(None)

        return callback(json)

    def _signature(self, kwargs):
        parts = ['%s=%s' % (n, kwargs[n]) for n in sorted(kwargs.keys())]
        body = ''.join(parts) + self._facebook_secret
        if isinstance(body, unicode):
            body = body.encode('utf-8')

        return hashlib.md5(body).hexdigest()
