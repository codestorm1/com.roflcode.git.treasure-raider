from google.appengine.ext import db

import logging
import re

from pyramid.main.models import Container_user
from myspace.myspaceapi import MySpace

# MySpace consumer key and secret
# MYSPACE_CONSUMER_KEY = 'http://www.myspace.com/493100969'
# MYSPACE_CONSUMER_SECRET = '1938f0cade66465aa330949d206ab0e8e78460f9ddfc4ea5bfd88067a4478be4'

# app id 181948 external IFrame
MYSPACE_CONSUMER_KEY = 'http://www.roflcode.com/pyramid/appXml/top_of_the_pyramid_myspace.xml'
MYSPACE_CONSUMER_SECRET = '39487c9765fa474db023f64b41b67a38c13594b9bd8e4074a97a94adbf3e2ee1'


class Friends_controller(object):

#    def formatExceptionInfo(self, maxTBlevel=5):
#        cla, exc, trbk = sys.exc_info()
#        excName = cla.__name__
#        try:
#            excArgs = exc.__dict__["args"]
#        except KeyError:
#            excArgs = "<no args>"
#        excTb = traceback.format_tb(trbk, maxTBlevel)
#        return (excName, excArgs, excTb)
    
    def get_friends_v08(self, user_id):
        ''' hasApp returns only when true
        '''
        myspace = MySpace(MYSPACE_CONSUMER_KEY, MYSPACE_CONSUMER_SECRET)
        moreFriends = True
        page = 1
        page_size = 50
        max_friends = 1000
        friends = []
        while moreFriends:
            users = myspace.get_friends(user_id, page, page_size) #list='app'
            for friend in users['Friends']:
                friends.append(int(friend['userId']))
            if len(users['Friends']) < page_size or len(friends) > max_friends:
                moreFriends = False
            page += 1
        friends = friends[:max_friends]
        return users

    def get_friend_ids_v09(self, user_id):
        myspace = MySpace(MYSPACE_CONSUMER_KEY, MYSPACE_CONSUMER_SECRET)
        moreFriends = True
        page_size = 50
        max_friends = 1000
        start_index = 1
        friend_ids = []
        find_id = re.compile("\d+$")
        while moreFriends:
            person_id = 'myspace.com.person.%s' % user_id
            friends = myspace.get_friends_v09(person_id=person_id, get_friends=True, start_index=start_index, count=page_size)
            for friend in friends['entry']:
                person = friend['person']
                match = re.search(find_id, person['id'])
                friend_id = int(match.group(0))
                friend_ids.append(friend_id)
            if len(friends['entry']) < page_size or len(friend_ids) > max_friends:
                moreFriends = False
            start_index += page_size
        friend_ids = friend_ids[:max_friends]
        return friend_ids

#    def get_container_users_from_character(self, character):
#        query = Character.all()
#        query.filter('character', character) 
#        container_users = query.(100)
#        return container_users

    def get_profile_basic(self, user_id):
        myspace = MySpace(MYSPACE_CONSUMER_KEY, MYSPACE_CONSUMER_SECRET)
        profile = myspace.get_profile_basic(user_id)
        return profile

    def get_profile_full(self, user_id):
        myspace = MySpace(MYSPACE_CONSUMER_KEY, MYSPACE_CONSUMER_SECRET)
        profile = myspace.get_profile_full(user_id)
        return profile

    def get_profile_extended(self, user_id):
        myspace = MySpace(MYSPACE_CONSUMER_KEY, MYSPACE_CONSUMER_SECRET)
        profile = myspace.get_profile_extended(user_id)
        return profile
    
    
    def save_container_friends(self, container_user, friends):
        ''' takes a list of friends and saves to data store
            the friend list is gathered by the browser and sent via ajax
        '''
        saved = 0
        failed = 0
        if not container_user.character:
            return saved, failed
        
        user_friend_ids = set() # set(container_user.friend_ids) don't save existing friends
        character_keys = set()

#    has_app = db.BooleanProperty()
#    friend_ids = db.StringListProperty()
#    character = db.ReferenceProperty(reference_class=Character)

        for friend in friends.itervalues():
            domain = container_user.domain
            user_id = friend['id']
            try:
                profile_image_url = db.Link(friend['thumbnailUrl'])
            except Exception, e:
                logging.debug('bad thumbnail url (or no image) for friend: %s' % friend)
                logging.debug(e)
                profile_image_url = 'http://static.ak.fbcdn.net/rsrc.php/zBPOE/hash/k9bm7yii.gif' #use facebook no-pic image
                failed += 1
                continue
                
            user_key = domain + ":" + user_id;
            user = Container_user.get_by_key_name(user_key)
#            if not user:
#                user = Container_user(key_name = user_key,
#                                        container_user_id = user_id,
#                                        domain = domain,
#                                        character = None,
#                                        display_name = friend['displayName'],
#                                        profile_image_url = profile_image_url)
#            else: #update existing fields:
            if user:
                user.display_name = friend['displayName']
                user.profile_image_url = profile_image_url
                if user.character:
                    character_keys.add(user.character.key()) #this friend has a character.  Add it to the character's friend list
                if 'profileUrl' in friend:
                    user.profile_url = db.Link(friend['profileUrl'])
                user.ip_address = "1.2.3.4"
                if friend.has_key('hasAppInstalled'):
                    user.has_app = friend['hasAppInstalled']
                else:
                    user.has_app = False
                user.friend_ids = []
                user.put()
                user_friend_ids.add(user.container_user_id)
                saved += 1

        container_user.friend_count = len(user_friend_ids)
        container_user.friend_ids = list(user_friend_ids)
        container_user.put()
        # replace all container user friends

        #character_keys = set(container_user.character.friend_keys).union(character_keys) 
        # with above line uncommented, adds to friends, but doens't replace all.  Deleted friends won't be reomved, but multiple container friends would stay
        container_user.character.friend_count = len(character_keys)
        container_user.character.friend_keys = list(character_keys)
        container_user.character.put()
        # add friends from this container to the character friends
            
        return saved, failed
    
    def make_safe(self, unsafe_string):
        safe_string = re.sub(r'[\'\"<>`]', ' ', unsafe_string)
        return safe_string
            
    def refresh_container_friends(self, container_user):
        ''' gets container friends via REST API and saves to data store
        '''
        #container_user.friend_ids = self.get_friend_ids_v08(container_user.container_user_id)
        logging.info('in load container friends, id is %s' % container_user.container_user_id)
        friends = self.get_friends_v08(container_user.container_user_id)
        logging.info('friends: %s' % friends)
        user_friends = set(container_user.friend_ids)
        simple_users = {}
        friend_keys = set()

        for friend in friends['Friends']:
            domain = 'myspace.com'
            user_id = str(friend['userId'])
            user_key = domain + ":" + user_id;
            user = Container_user.get_by_key_name(user_key)
            if user == None:
                logging.debug('user not found at friend %s' % friend)
                logging.debug('user not found at userid %s' % user_id)
                #raise Exception('no user? wtf?')
                user = Container_user(key_name = user_key,
                                      display_name = self.make_safe(friend['name']),
                                        container_user_id = user_id,
                                        domain = domain,
                                        profile_url = db.Link(friend['webUri']),
                                        profile_image_url = db.Link(friend['largeImage']),
                                        character = None)
            else:
                if user.character:
                    friend_keys.add(user.character.key())
                    
            user.ip_address = "1.2.3.4"
            if friend.has_key('hasAppInstalled'):
                user.has_app = friend['hasAppInstalled']
            else:
                user.has_app = False
            user.friend_ids = []
            user.put()
            user_friends.add(user.container_user_id)
            
            simple_user = {}
            simple_user['user_id'] = user.container_user_id
            simple_user['domain'] = user.domain
            simple_user['display_name'] = user.display_name
            simple_user['has_app'] = user.has_app
            simple_users[user.container_user_id] = simple_user
             
        container_user.friend_ids = list(user_friends)
        container_user.friend_count = len(user_friends)
        container_user.put()
        
        if container_user.character:
            container_user.character.friend_count = len(friend_keys)
            container_user.character.friend_keys = list(friend_keys)
            container_user.character.put()
        
        # todo: popuplate character friends
        logging.debug('exit container friends')
        return simple_users #for json serialization

