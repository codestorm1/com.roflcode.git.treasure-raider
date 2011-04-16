import logging
import re

from datetime import datetime

from facebook import Facebook
from facebook import FacebookError

from pyramid.main.models import Container_user
from pyramid.main.models import Caller_context

from pyramid.main.friends_controller import Friends_controller
from pyramid.main.accountController import AccountController

facebook_api_key = '9ec365507d3993b54c38962b551e7c7e'
facebook_secret = '6994039c6f1f8837a4bd80caaadf0e33'
#Application ID 355059065973

class User_controller(object):
    
    
#myspace profile basic: {u'name': u'X[\u0a28\u0a40\u01b8\u0335\u0321\u2192Ramses\u2190\u01b7\u0a17\u0a47 DaGreat&lt;&#39;&#39;:&gt;', u'largeImage': u'http://c3.ac-images.myspacecdn.com/images02/89/l_90ec1367723d499da7c14bbc467f80de.jpg', u'image': u'http://c3.ac-images.myspacecdn.com/images02/89/s_90ec1367723d499da7c14bbc467f80de.jpg', u'userId': 493100288, u'uri': u'http://api.myspace.com/v1/users/493100288', u'webUri': u'http://www.myspace.com/493100288', u'lastUpdatedDate': u'9/24/2010 11:23:32 AM', u'type': u'basic'}
#myspace profile full: {u'city': None, u'maritalstatus': u'Single', u'country': u'US', u'aboutme': u'', u'hometown': u'', u'culture': u'en-US', u'basicprofile': {u'name': u'X[\u0a28\u0a40\u01b8\u0335\u0321\u2192Ramses\u2190\u01b7\u0a17\u0a47 DaGreat&lt;&#39;&#39;:&gt;', u'largeImage': u'http://c3.ac-images.myspacecdn.com/images02/89/l_90ec1367723d499da7c14bbc467f80de.jpg', u'image': u'http://c3.ac-images.myspacecdn.com/images02/89/s_90ec1367723d499da7c14bbc467f80de.jpg', u'userId': 493100288, u'uri': u'http://api.myspace.com/v1/users/493100288', u'webUri': u'http://www.myspace.com/493100288', u'lastUpdatedDate': u'9/24/2010 11:23:32 AM'}, u'gender': u'Male', u'postalcode': u'65432', u'region': u'', u'type': u'full', u'age': 40}
#myspace profile ex: {u'interests': u'', u'fullprofile': {u'city': None, u'maritalstatus': u'Single', u'country': u'US', u'aboutme': u'', u'hometown': u'', u'culture': u'en-US', u'basicprofile': {u'name': u'X[\u0a28\u0a40\u01b8\u0335\u0321\u2192Ramses\u2190\u01b7\u0a17\u0a47 DaGreat&lt;&#39;&#39;:&gt;', u'largeImage': u'http://c3.ac-images.myspacecdn.com/images02/89/l_90ec1367723d499da7c14bbc467f80de.jpg', u'image': u'http://c3.ac-images.myspacecdn.com/images02/89/s_90ec1367723d499da7c14bbc467f80de.jpg', u'userId': 493100288, u'uri': u'http://api.myspace.com/v1/users/493100288', u'webUri': u'http://www.myspace.com/493100288', u'lastUpdatedDate': u'9/24/2010 11:23:32 AM'}, u'gender': u'Male', u'postalcode': u'65432', u'region': u'', u'age': 40}, u'television': u'', u'mood': u'(none)', u'headline': None, u'status': u'', u'movies': u'', u'books': u'', u'desiretomeet': u'', u'music': u'', u'heroes': u'', u'type': u'extended', u'zodiacsign': u'Aries', u'occupation': u''}

    
    
    def get_myspace_viewer_info(self, user_id):
        viewer_info = None
        friends_controller = Friends_controller()
        profile = friends_controller.get_profile_full(user_id)
        if profile:
            logging.info('myspace profile full: %s' % profile)
        profile = friends_controller.get_profile_extended(user_id)
        if profile:
            logging.info('myspace profile ex: %s' % profile)
        profile = friends_controller.get_profile_basic(user_id)
        if profile:
            logging.info('myspace profile basic: %s' % profile)
            
            viewer_info = {}
            viewer_info['container_user_id'] = user_id
            viewer_info['domain'] = 'myspace.com'
            viewer_info['display_name'] = re.sub(r'[\'\"<>`]', ' ', profile['name'])
            viewer_info['profile_url'] = re.sub(r'[\'\"<>`]', ' ', profile['webUri'])
            viewer_info['profile_image_url'] = re.sub(r'[\'\"<>`]', ' ', profile['image'])
        else:
            logging.warn('no myspace profile found for user id %s' % user_id)
        return viewer_info
    
    def get_facebook_viewer_info(self, user_id):
        fb = Facebook(facebook_api_key, facebook_secret)
        
        viewer_info = {}
        fb.uid = user_id
        viewer_info['container_user_id'] = fb.uid
        viewer_info['domain'] = 'facebook.com'
        try:
            info = fb.users.getInfo([fb.uid], ['name', 'pic', 'profile_url'])
            if len(info) > 0:
                viewer_info['display_name'] = info[0]['name']
                viewer_info['display_name'] = re.sub(r'[\'\"<>`]', ' ', viewer_info['display_name'])
                viewer_info['profile_url'] = info[0]['profile_url']
                viewer_info['profile_image_url'] = info[0]['pic']
                return viewer_info
        except FacebookError, e:
            logging.info('exception getting facebook user info: %s' % e)
            # Error 102 means the session has expired.
            logging.info(e.code)
            if e.code == u'102':
                logging.info('equals u102')
                return viewer_info
            logging.info('not equal to u102 [%s]' % e.code)
        return viewer_info

    def get_mock_viewer_info(self, user_id):
        fake_users = { '493100288': # Firefox
             {
                           'container_user_id' : '493100288',
                           'domain' : 'myspace.com',
                           'display_name' : 'Mac Playa',
                            'profile_image_url' : 'http://img2.orkut.com/images/medium/1241866866/475841126/ep.jpg',},
            '11111' : # Chrome
            {
                           'container_user_id' : '11111',
                           'domain' : 'myspace.com',
                           'display_name' : 'Brazil1 Pyrtest',
                           'profile_image_url' : 'http://img1.orkut.com/images/small/1275754135/606110152/ln.jpg',},
            '11693727946268894447' :   #Safari
            {
                           'container_user_id' : '11693727946268894447',
                           'domain' : 'orkut.com',
                           'display_name' : 'Orkut Mac Playa',
                           'profile_image_url' : 'http://profile.ak.fbcdn.net/v223/12/32/n100000884291778_6109.jpg',},
            '22222' : #Flock
             {
                           'container_user_id' : '22222',
                           'domain' : 'orkut.com',
                           'display_name' : 'Flock Local Playa',
                           'profile_image_url' : 'http://img4.orkut.com/images/small/1275752484/574434232/ep.jpg',},
        '33333' :#Opera
             {
                           'container_user_id' : '33333',
                           'domain' : 'orkut.com',
                           'display_name' : 'Opera Local Playa',
                           'profile_image_url' : 'http://img1.orkut.com/images/small/1264876324/516126254/ln.jpg',},
        '493100288' : # ???
            {
               'container_user_id' : '493100288',
               'domain' : 'myspace.com',
               'display_name' : 'Mac Playa',
               'profile_image_url' : 'http://img2.orkut.com/images/medium/1241866866/475841126/ep.jpg',},
            
            }
        viewer_info = None
        if user_id in fake_users:
            viewer_info = fake_users[user_id]
        viewer_info['profile_url'] = 'http://www.roflcode.com/noprofile'
        return viewer_info
    
    
    
    def get_refresh_or_create_container_user(self, domain, container_user_id):
        viewer_info = None
        logging.info('get refresh or create for domain %s container_user %s' % (domain, container_user_id))
        try:
            if domain == 'myspace.com':
                viewer_info = self.get_myspace_viewer_info(container_user_id)
                logging.info('myspace profile: %s' % viewer_info)
            elif domain == 'facebook.com' :
                viewer_info = self.get_facebook_viewer_info(container_user_id)
                logging.info('facebook profile: %s' % viewer_info)
            elif domain == 'mock' :
                viewer_info = self.get_mock_viewer_info(container_user_id)
                domain = viewer_info['domain']
                logging.info('mock profile: %s' % viewer_info)
            else:                
                logging.info('unknown domain - can\'t set viewer info')
        except Exception, e:
            logging.info('wtf excep')
            logging.exception(e)
        logging.info('looking up container user')
        logging.debug('trying debug log')
        container_user_key = domain + ":" + container_user_id
        container_user = Container_user.get_by_key_name(container_user_key)
        
        if container_user:
            #container user already associated with pyramid user
            logging.info('found container user, checking for changes')
            
            if viewer_info:
                if 'display_name' in viewer_info and container_user.display_name != viewer_info['display_name']:
                    container_user.display_name = viewer_info['display_name']
                if 'profile_image_url' in viewer_info and container_user.profile_image_url != viewer_info['profile_image_url']:
                    container_user.profile_image_url = viewer_info['profile_image_url']
                if 'profile_url' in viewer_info and container_user.profile_url != viewer_info['profile_url']:
                    container_user.profile_url = viewer_info['profile_url']
        else:
            #associate container user with pyramid user
            logging.info('no container user found, creating one')
            if viewer_info:
                container_user = Container_user(key_name = container_user_key, 
                                                container_user_id = viewer_info['container_user_id'],
                                                character = None,
                                                domain = viewer_info['domain'],
                                                display_name = viewer_info['display_name'],
                                                profile_url = viewer_info['profile_url'],
                                                profile_image_url = viewer_info['profile_image_url'],
                                                ip_address = "1.2.3.4",
                                                link_date = datetime.now(),
                                                first_install_date = datetime.now(),
                                                first_use_date = datetime.now(),
                                                last_install_date = datetime.now(),
                                                last_use_date = datetime.now(),
                                                has_app = True)
                container_user.put()
            else:
                logging.info('no viewer info')
        return container_user
