from django.utils import simplejson

from tipfy import (RequestHandler, RequestRedirect, Response, abort,
    cached_property, redirect, url_for)
from tipfy.ext.auth import MultiAuthMixin, login_required, user_required
from tipfy.ext.auth.facebook import FacebookMixin
from tipfy.ext.auth.facebookClientFlow import FacebookClientFlowMixin
from tipfy.ext.auth.facebookServerFlow import FacebookServerFlowMixin
from tipfy.ext.auth.friendfeed import FriendFeedMixin
from tipfy.ext.auth.google import GoogleMixin
from tipfy.ext.auth.twitter import TwitterMixin
from tipfy.ext.auth.model import User 


from tipfy.ext.jinja2 import Jinja2Mixin
from tipfy.ext.session import AllSessionMixins, SessionMiddleware
from tipfy.ext.wtforms import Form, fields, validators

from treasure_raider.middleware import EnvironmentMiddleware

# below from fb cookie example

#FACEBOOK_APP_ID = "3f2a276f14af70d2ee5d982bacdc2f7a"
#FACEBOOK_APP_SECRET = "11bc317fee74d3ccf61ef3bce720315b"

import facebookAPI
import logging

from urllib2 import HTTPError
import urllib
import urllib2


from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

#from treasure_raider.models import Experience_limits


REQUIRED = validators.required()

class LoginForm(Form):
    username = fields.TextField('Username', validators=[REQUIRED])
    password = fields.PasswordField('Password', validators=[REQUIRED])
    remember = fields.BooleanField('Keep me signed in')


class SignupForm(Form):
    nickname = fields.TextField('Nickname', validators=[REQUIRED])


class RegistrationForm(Form):
    username = fields.TextField('Username', validators=[REQUIRED])
    password = fields.PasswordField('Password', validators=[REQUIRED])
    password_confirm = fields.PasswordField('Confirm the password', validators=[REQUIRED])


class BaseHandler(RequestHandler, MultiAuthMixin, Jinja2Mixin,
    AllSessionMixins):
    middleware = [SessionMiddleware, EnvironmentMiddleware]

    def render_response(self, filename, **kwargs):
        auth_session = None
        if 'id' in self.auth_session:
            auth_session = self.auth_session

        self.request.context.update({
            'auth_session': auth_session,
            'current_user': self.auth_current_user,
            'login_url':    self.auth_login_url(),
            'logout_url':   self.auth_logout_url(),
            'current_url':  self.request.url,
            'facebook_app_id': self.app.get_config('tipfy.ext.auth.facebook', 'app_id')
        })
        if self.messages:
            self.request.context['messages'] = simplejson.dumps(self.messages)

        return super(BaseHandler, self).render_response(filename, **kwargs)

    def redirect_path(self, default='/'):
        if '_continue' in self.session:
            url = self.session.pop('_continue')
        else:
            url = self.request.args.get('continue', '/')

        if not url.startswith('/'):
            url = default

        return url

    def _on_auth_redirect(self, override_continue=None):
        """Redirects after successful authentication using third party
        services.
        """
        if override_continue:
            self.session.pop('_continue')  #sloppy crap I'm adding try to fix this fucking infinite loop
        
        if '_continue' in self.session:
            url = self.session.pop('_continue')
        else:
            url = '/'

        if not self.auth_current_user:
            url = self.auth_signup_url()

        return redirect(url)



class HomeHandler(BaseHandler):
    def get(self, **kwargs):
        return self.render_response('home.html')


def check_refresh_user(func):
    """A RequestHandler method decorator to refresh user info from container if stale.
    """
    def decorated(self, *args, **kwargs):
        return _check_refresh_user(self) or func(self, *args, **kwargs)

    return decorated


def _check_refresh_user(handler):
    
    error_messages = []
    if not handler.auth_session:
        logging.info('no auth session, redirecting to login')
        return redirect(handler.auth_login_url())

    if not handler.auth_current_user:
        logging.info('have auth session, no user, redirecting to signup')
        newUrl = redirect(handler.auth_signup_url())
        return newUrl
    
    def wrapper( *args, **kwargs):
        kwargs.update({'error_messages': error_messages}) # Edit the keyword arguments -- here, enable debug mode no matter what
#        print 'Calling function "%s" with arguments %s and keyword arguments %s' % (handler.__name__, args, kwargs)
        return handler('doit', *args, **kwargs)
    
    user = handler.auth_current_user
        
    FACEBOOK_APP_ID  = handler.app.get_config('tipfy.ext.auth.facebook', 'app_id')
    FACEBOOK_APP_KEY = handler.app.get_config('tipfy.ext.auth.facebook', 'api_key')
    FACEBOOK_APP_SECRET = handler.app.get_config('tipfy.ext.auth.facebook', 'app_secret')

#    fb_user = facebookAPI.get_user_from_cookie(handler.request.cookies, FACEBOOK_APP_KEY, FACEBOOK_APP_SECRET)
    
    cookie_token = handler.request.cookies.get("tr_fb_access_token")
    if cookie_token:
        user.access_token = cookie_token #update the access token
        error_messages.append('updated access token from TR cookie %s' % user.access_token)
    else:
        error_messages.append('no tr_fb_access_token cookie')
        logging.warning('no tr facebook cookie to read.')
        logging.warning('environment:' +  handler.app.get_config('tipfy.ext.auth.facebook', 'environment') + ' api key:' + FACEBOOK_APP_KEY)
        
#    if not user.access_token:
#        raise 'no access token, can\'t update user info'
    
    if user and user.access_token:
        graph = facebookAPI.GraphAPI(user.access_token)
        try:
            profile = graph.get_object("me")
            user.name = profile['name']
            friends = graph.get_connections("me", "friends")
            user.friend_ids = ['facebook|' + friend['id'] for friend in friends['data']]
            error_messages.append('friend list updated')
        except HTTPError, e:
            if e.headers['www-authenticate'].find('access token') != -1:
                token_error = 'facebook rejected access token %s' % user.access_token
                error_messages.append(token_error)
                logging.warning(token_error)
                logging.warning(e.headers['www-authenticate'])
                wrapper.attribute = 1
                return wrapper()
        finally:
            user.put() #update every time for now


class ContentHandler(BaseHandler):
    
    def doit(self, **kwargs):
        user = self.auth_current_user
        
        query = db.Query(User, keys_only=False)
        #container_keys = ['facebook|' + friend_id for friend_id in user.friend_ids]
        query.filter('friend_ids', user.auth_id)
#        query.order('-updated')

        friends = query.fetch(10000)
        
        kwargs.update( { 'friends' : friends })
        if 'error_messages' not in kwargs:
            kwargs['error_messages'] = []
        kwargs['error_messages'].append(str(len(friends)) + ' of ' + str(len(user.friend_ids)) + ' friends playing')
        
        
        return self.render_response('content.html', **kwargs)

#    @check_refresh_user
    @user_required
    def get(self, **kwargs):
        return self.doit(**kwargs)

#    @check_refresh_user    
    @user_required
    def post(self, **kwargs):
        return self.doit(**kwargs)


class ExampleHandler(BaseHandler):
    """Show recent runs for the user and friends"""
    def doit(self, **kwargs):
        kwargs = dict(current_user=self.current_user,
                    facebook_app_id=self.app.get_config(__name__, 'api_key'))
        return self.render_response('fb_cookie_example.html', **kwargs)

    def head(self, **kwargs):
        ''' Facebook makes a head request first
        '''
        return Response('')

    def get(self, **kwargs):
        return self.doit(**kwargs)

    def post(self, **kwargs):
        return self.doit(**kwargs)


class LoginHandler(BaseHandler):
    def get(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth_current_user:
            # User is already registered, so don't display the signup form.
            logging.info('login handler: user found, so redirecting to: %s' % redirect_url)
            return redirect(redirect_url)

        opts = {'continue': self.redirect_path()}
        context = {
            'form':                 self.form,
            'facebook_login_url':   url_for('auth/facebook', **opts),
            'facebook_server_flow_login_url':   url_for('auth/facebookserverflow', **opts),
            'friendfeed_login_url': url_for('auth/friendfeed', **opts),
            'google_login_url':     url_for('auth/google', **opts),
            'twitter_login_url':    url_for('auth/twitter', **opts),
            'yahoo_login_url':      url_for('auth/yahoo', **opts),
        }
        context['facebook_api_key'] = self.app.get_config('tipfy.ext.auth.facebook', 'api_key')        
        return self.render_response('login.html', **context)

    def post(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth_current_user:
            # User is already registered, so don't display the signup form.
            return redirect(redirect_url)

        if self.form.validate():
            username = self.form.username.data
            password = self.form.password.data
            remember = self.form.remember.data

            res = self.auth_login_with_form(username, password, remember)
            if res:
                return redirect(redirect_url)

        self.set_message('error', 'Authentication failed. Please try again.',
            life=None)
        return self.get(**kwargs)

    @cached_property
    def form(self):
        return LoginForm(self.request)


class LogoutHandler(BaseHandler):
    def get(self, **kwargs):
        self.auth_logout()
        return redirect(self.redirect_path())


class SignupHandler(BaseHandler):
    @login_required
    def get(self, **kwargs):
        if self.auth_current_user:
            # User is already registered, so don't display the signup form.
            return redirect(self.redirect_path())

        return self.render_response('signup.html', form=self.form)


    ''' BG: here, we got the nickname form post, we'll read user data from session and create the user in datastore 
    '''
    @login_required
    def post(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth_current_user:
            # User is already registered, so don't process the sign up form.
            return redirect(redirect_url)

        if self.form.validate():
            auth_id = self.auth_session.get('id')
            kwargs['uid'] = str(self.auth_session.get('uid'))
            kwargs['name'] = self.auth_session.get('name')
            kwargs['profile_url'] = self.auth_session.get('profile_url')
            kwargs['profile_image_url'] = 'http://graph.facebook.com/%s/picture' % str(self.auth_session.get('uid'))

            kwargs['access_token'] = self.auth_session.get('access_token')
            kwargs['expires_seconds'] = self.auth_session.get('expires_seconds')
            kwargs['friend_ids'] = self.auth_session.get('friend_ids')
            
            user = self.auth_create_user(username=self.form.nickname.data, auth_id=auth_id, **kwargs)
            if user:
                self.auth_set_session(user.auth_id, user.session_id, '1')
                
                self.set_message('success', 'You are now registered. '
                    'Welcome!', flash=True, life=5)
                return redirect(redirect_url)
            else:
                self.set_message('error', 'This nickname is already '
                    'registered.', life=None)
                return self.get(**kwargs)

        self.set_message('error', 'A problem occurred. Please correct the '
            'errors listed in the form.', life=None)
        return self.get(**kwargs)

    @cached_property
    def form(self):
        return SignupForm(self.request)

''' BG - not gonna use this manual auth
'''
class RegisterHandler(BaseHandler):
    def get(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth_current_user:
            # User is already registered, so don't display the registration form.
            return redirect(redirect_url)

        return self.render_response('register.html', form=self.form)

    def post(self, **kwargs):
        redirect_url = self.redirect_path()

        if self.auth_current_user:
            # User is already registered, so don't process the signup form.
            return redirect(redirect_url)

        if self.form.validate():
            username = self.form.username.data
            password = self.form.password.data
            password_confirm = self.form.password_confirm.data

            if password != password_confirm:
                self.set_message('error', "Password confirmation didn't match.",
                    life=None)
                return self.get(**kwargs)

            auth_id = 'own|%s' % username
            user = self.auth_create_user(username, auth_id, password=password)
            if user:
                self.auth_set_session(user.auth_id, user.session_id, '1')
                self.set_message('success', 'You are now registered. '
                    'Welcome!', flash=True, life=5)
                return redirect(redirect_url)
            else:
                self.set_message('error', 'This nickname is already '
                    'registered.', life=None)
                return self.get(**kwargs)

        self.set_message('error', 'A problem occurred. Please correct the '
            'errors listed in the form.', life=None)
        return self.get(**kwargs)

    @cached_property
    def form(self):
        return RegistrationForm(self.request)


class FacebookAuthHandler(BaseHandler, FacebookMixin):
    def head(self, **kwargs):
        """Facebook will make a HEAD request before returning a callback."""
        return Response('')

    def get(self):
        url = self.redirect_path()

        if 'id' in self.auth_session:
            # User is already signed in, so redirect back.
            return redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('session', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authenticate_redirect()

    def _on_auth(self, user):
        """
        """
        if not user:
            abort(403)

        # try user name, fallback to uid.
        uid = str(user.get('uid', ''))
        username = user.get('username', None)
        if not username:
            username = uid
            
        kwargs = user

        auth_id = 'facebook|%s' % uid
        logging.debug('auth_id is ' + auth_id + ' uid is ' + uid)
        self.auth_login_with_third_party(auth_id=auth_id, remember=True, **kwargs)
        return self._on_auth_redirect()

class FacebookClientFlowAuthHandler(BaseHandler, FacebookClientFlowMixin):

    def get(self):
        url = self.redirect_path()

        if 'id' in self.auth_session:
            # User is already signed in, so redirect back.
            return redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('tr_fb_access_token', None): #normally this request is coming from facebook
            return self.get_authenticated_user(self._on_auth)
        
        logging.info('in FB client flow.  doing self.authenticate_redirect()')
        return self.authenticate_redirect() #send user to facebook, along with 'next' param to bring them back here

    def _on_auth(self, user):
        """
        """
        if not user:
            abort(403)

        # try user name, fallback to uid.
        uid = str(user.get('uid', ''))
        username = user.get('username', None)
        if not username:
            username = uid
            
        kwargs = user

        auth_id = 'facebook|%s' % uid

        logging.info('attempting 3rd party login') 
        self.auth_login_with_third_party(auth_id=auth_id, remember=True, **kwargs)
        redirect =  self._on_auth_redirect(override_continue=True)
        
        logging.info('_on_auth redirecting to: %s' % redirect.headers['Location']) 
        return redirect

class FacebookServerFlowAuthHandler(BaseHandler, FacebookServerFlowMixin):


    def get(self):
        url = self.redirect_path()

        if 'id' in self.auth_session:
            # User is already signed in, so redirect back.
            return redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('code', None): #normally this request is coming from facebook
            return self.get_authenticated_user(self._on_auth)
        
        logging.info('in FB server flow.  doing self.authenticate_redirect()')
        return self.authenticate_redirect() #send user to facebook, along with 'next' param to bring them back here

    def _on_auth(self, user):
        """
        """
        if not user:
            abort(403)


        # try user name, fallback to uid.
        uid = str(user.get('uid', ''))
        username = user.get('username', None)
        if not username:
            username = uid
        
        _user = {}
        _user['uid'] = uid
        _user['name'] = user.get('name')
        _user['access_token'] = user.get('access_token')
        _user['expires_seconds'] = user.get('expires_seconds')
        _user['first_name'] = user.get('first_name')
        _user['last_name'] = user.get('last_name')
        _user['username'] = user.get('username')
        _user['profile_url'] = user.get('link')
        _user['friend_ids'] = user['friend_ids']
        #_user[''] = user['']

        kwargs = _user

        auth_id = 'facebook|%s' % uid

        logging.info('attempting 3rd party login') 
        self.auth_login_with_third_party(auth_id=auth_id, remember=True, **kwargs)
        
        redirect = self._on_auth_redirect(override_continue=True)
        logging.info('_on_auth redirecting to: %s' % redirect.headers['Location']) 
        return redirect

class FriendFeedAuthHandler(BaseHandler, FriendFeedMixin):
    """
    """
    def get(self):
        url = self.redirect_path()

        if 'id' in self.auth_session:
            # User is already signed in, so redirect back.
            return redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('oauth_token', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authorize_redirect()

    def _on_auth(self, user):
        if not user:
            abort(403)

        auth_id = 'friendfeed|%s' % user.pop('username', '')
        self.auth_login_with_third_party(auth_id, remember=True,
            access_token=user.get('access_token'))
        return self._on_auth_redirect()


class TwitterAuthHandler(BaseHandler, TwitterMixin):
    def get(self):
        url = self.redirect_path()

        if 'id' in self.auth_session:
            # User is already signed in, so redirect back.
            return redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('oauth_token', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authorize_redirect()

    def _on_auth(self, user):
        if not user:
            abort(403)

        auth_id = 'twitter|%s' % user.pop('username', '')
        self.auth_login_with_third_party(auth_id, remember=True,
            access_token=user.get('access_token'))
        return self._on_auth_redirect()


class GoogleAuthHandler(BaseHandler, GoogleMixin):
    def get(self):
        url = self.redirect_path()

        if 'id' in self.auth_session:
            # User is already signed in, so redirect back.
            return redirect(url)

        self.session['_continue'] = url

        if self.request.args.get('openid.mode', None):
            return self.get_authenticated_user(self._on_auth)

        return self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            abort(403)

        auth_id = 'google|%s' % user.pop('email', '')
        self.auth_login_with_third_party(auth_id, remember=True)
        return self._on_auth_redirect()
    
    
    
