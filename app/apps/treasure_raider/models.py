from datetime import datetime
from google.appengine.ext import db

#from tipfy.ext.auth import User #circular reference?

import os
import logging
import random

class Account(db.Model):
    currency_type = db.StringProperty(required=True, choices=('coins', 'cash'))
    balance =  db.IntegerProperty(required=True, default=0)
    negative_balance_allowed = db.BooleanProperty(required=True, default=False)

class Character(db.Model):
    ''' turn into polymodel, or set up default values in bulkloader, so more properties can be "required"
    '''
    character_name = db.StringProperty(required=True)
    image_url = db.LinkProperty(required=True)
    language = db.StringProperty()
    country = db.StringProperty()
    ip_address = db.StringProperty()
    coins_account = db.ReferenceProperty(reference_class=Account, collection_name = 'coins_account_set')
    cash_account = db.ReferenceProperty(reference_class=Account, collection_name = 'cash_account_set')
    experience_points = db.IntegerProperty()
    experience_level = db.IntegerProperty()
    acknowledged_experience_level = db.IntegerProperty()
    invited_by = db.SelfReferenceProperty(default=None, collection_name="invited_by_set")
    creation_date = db.DateTimeProperty()
    is_fake = db.BooleanProperty(required=True)
    tutorial_on = db.BooleanProperty() # add this property to fake chars so prop can be required=True
    friend_count = db.IntegerProperty()
    friend_keys = db.ListProperty(item_type=db.Key)
    is_deleted = db.BooleanProperty(default=False)

    @staticmethod
    def create(config, user, image_url, is_fake):
        '''create new character
        todo: seems redundant to have coins_account with character as parent,
        and Account reference type for coins account as character property,
        requires an extra put()
        '''

        character = Character(parent=user,#key_name=character_name, #to key or not to key <- answer, no key
            character_name=user.username,
            creation_date = datetime.utcnow(),
            language = "xx",
            country = "XX",
            ip_address = "1.2.3.4",
            experience_points = 0,
            experience_level = 1,
            acknowledged_experience_level = 1,
            invited_by = None,
            image_url = image_url,
            is_fake = is_fake,
            friend_keys = [],
            tutorial_on = True)
        character.put()
        Hunt_grid.create(config, character)
        #hunt_grid.populate()
        
        currency_type = 'coins'
        key_name = '%s_%s' % (character.character_name, currency_type)
        coins_account = Account(parent=character,
                               key_name=key_name,
                               currency_type=currency_type,
                               negative_balance_allowed=False, 
                               balance=config.starting_coins)

        currency_type = 'cash'
        key_name = '%s_%s' % (character.character_name, currency_type)
        cash_account = Account(parent=character,
                               key_name=key_name,
                               currency_type=currency_type, 
                               negative_balance_allowed=False, 
                               balance=config.starting_cash)
        db.put((coins_account, cash_account))

        character.coins_account = coins_account
        character.cash_account = cash_account
        character.put()
        return character


    def get_hunt_grid(self):
        hunt_grid = Hunt_grid.get_by_key_name(key_names=self.key().name(),
                                            parent=self)
        return hunt_grid


#class Container_user(db.Model):
#    container_user_id = db.StringProperty(required=True)
#    domain = db.StringProperty(required=True)
#    display_name = db.StringProperty() # not requiring anymore (required=True)
#    profile_url = db.LinkProperty()
#    profile_image_url = db.LinkProperty()
#    ip_address = db.StringProperty()
#    link_date = db.DateTimeProperty()
#    first_install_date = db.DateTimeProperty()
#    first_use_date = db.DateTimeProperty()
#    last_install_date = db.DateTimeProperty()
#    last_use_date = db.DateTimeProperty()
#    has_app = db.BooleanProperty()
#    friend_count = db.IntegerProperty()
#    friend_ids = db.StringListProperty(required=True)
#    character = db.ReferenceProperty(reference_class=Character)
#    is_deleted = db.BooleanProperty(default=False)
    
    
#class Player_invite(db.Model):
#    ''' invited may not have joined game yet and may not have a container_user.  
#        Lookups must be done by container id.
#    '''
#    inviter_container_user = db.ReferenceProperty(required=True, reference_class=User, collection_name="container_inviter_set")
#    inviter_character = db.ReferenceProperty(required=True, reference_class=Character, collection_name="player_inviter_set")
#    inviter_brick_description = db.StringProperty(required=True) #brick can move to a new entity after a pyramid split.  Description is unique, and better for lookups
#    
#    domain = db.StringProperty()  #leave these blank for character invites?  easier to query since GAE has no "or" queries?
#    invitee_container_user_id = db.StringProperty() #either invite by domain/container_user_id,
#    
#    invitee_container_user = db.ReferenceProperty(reference_class=User, collection_name="container_user_invitee_set") # or by container_user/character if player is already in game
#    invitee_character = db.ReferenceProperty(reference_class=Character, collection_name="character_invitee_set") 
#
#    invitee_bricks = db.ListProperty(item_type=db.Key, required=True, default=[]) # joined bricks if invite resulted in joins, list because the same invite could be re-sent to same invitee
#    invite_successful = db.BooleanProperty(default=None)
#
#    is_active = db.BooleanProperty(default=True)
#    invite_time = db.DateTimeProperty(auto_now_add=True)
    
    # if the game suggests a pyramid to a new player, use game for invite
    # if a player randomly finds a pyramid to join, it is not a game invite

class Message(db.Model):
    message_type = db.IntegerProperty(required=True)
    # 1 won pyramid
    # 2 expiring
    
    recipient = db.ReferenceProperty(reference_class=Character, collection_name="recipient_set", required=True)
    sender = db.ReferenceProperty(reference_class=Character, collection_name="sender_set", default=None) # None = game message
    title = db.StringProperty # optional title for message box
    body = db.StringProperty(required=True)
    link = db.URLProperty()
    image = db.URLProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    is_deleted = db.BooleanProperty(default=False)
    read_by_user = db.BooleanProperty(default=False)
    pop_message_box = db.BooleanProperty(default=False) # if True, a message box will be popped up the next time the user joins the game
    

#class Game_invite(db.Model):
#    pyramid = db.ReferenceProperty(reference_class=Pyramid)  
#    invitee = db.ReferenceProperty(reference_class=Character, collection_name="game_invitee_set")
#    invite_successful = db.BooleanProperty()
#    invitee_joined_brick = db.ReferenceProperty(reference_class=Brick, collection_name="game_invitee_brick_set") # joined brick if invite resulted in a join
#    invite_time = db.DateTimeProperty(auto_now_add=True)
  
#def update_character(self):
#obj = db.get(self.key())
#make this a tranactional update
    
    
# todo: the following 2 classes are worthless and should be converted to dicts    
class Caller_context(object):
    output_type = 'full'
    base_root = ''
    static_root = ''
    domain_type = ''
    platform = None

class Positions(object):
    position_abs = 0
    position_rel = 0
    
class Offerpal_deposit(db.Model):
    offerpal_id = db.StringProperty(required=True)
    snuid =  db.StringProperty(required=True)
    account = db.ReferenceProperty(reference_class=Account)
    currency_type = db.StringProperty(required=True, choices=('cash',))
    deposit_amount = db.IntegerProperty(required=True) # record this here in addition to Account and Account_transfer 
    verifier = db.StringProperty(required=True)
    verified = db.BooleanProperty(required=True)
    affl = db.StringProperty() # optional tracking parameter
    error = db.StringProperty() # if this exists, need to contact offerpal
    response_code = db.IntegerProperty(required=True) # HTTP code returned to offerpal
    found_user = db.BooleanProperty()
    success = db.BooleanProperty(required=True)
    timestamp = db.DateTimeProperty(required=True, auto_now_add=True)
    
class Account_transfer(db.Model):
    ''' parent is the account
        key_name is counter_account key for destination accounts, not used for source accounts
    '''
    amount = db.IntegerProperty(required=True)
    currency_type = db.StringProperty(required=True, choices=('cash', 'coins'))
    self_account = db.ReferenceProperty(Account, required=True, collection_name="self_account_set") # this is redundant, the account is also the parent
    counter_account = db.ReferenceProperty(Account, required=True, collection_name="counter_account_set") # the account that is debited as this account is credited or vice versa 
    counter_transfer = db.SelfReferenceProperty(collection_name="counter_transfer_set")
    timestamp = db.DateTimeProperty(required=True, auto_now_add=True)
    is_committed = db.BooleanProperty(required=True)

class Daily_reward(db.Model):
    date = db.DateProperty(required=True)
    coins_account = db.ReferenceProperty(reference_class=Account)
    
class Reward_entry(db.Model):
    ''' keeping this simpler than account transfers, just keep a record of each experience increase
    '''
    character = db.ReferenceProperty(Character, required=True)
    description = db.StringProperty(required=True)
    currency_type = db.StringProperty(required=True)
    amount = db.IntegerProperty(required=True)
    timestamp = db.DateTimeProperty(required=True, auto_now_add=True)

class Experience_limits(db.Model):
    experience_level = db.IntegerProperty(required=True)
    min_experience_points = db.IntegerProperty(required=True)
    next_experience_points = db.IntegerProperty(required=True)
    air_capacity_reward = db.IntegerProperty(required=True)
    group = db.StringProperty(required=True) #required=True)
    cash_reward = db.IntegerProperty(required=True)
    coins_reward = db.IntegerProperty(required=True)
    
class Config(db.Model):
    ''' main game configuration
    '''
    experience_limits_group = db.StringProperty(required=True)
    starting_cash = db.IntegerProperty(required=True)
    starting_coins = db.IntegerProperty(required=True)
    hunt_zone_max_air = db.IntegerProperty(required=True)
    daily_air_refresh_rate = db.IntegerProperty(required=True)
    hunt_grid_horizontal_squares = db.IntegerProperty(required=True)
    hunt_grid_vertical_squares = db.IntegerProperty(required=True)
    
    @staticmethod
    def get_for_current_environment():
        debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')
        environment = 'development' if debug else 'production'
        config = Config.get_by_key_name(environment)
        if config is None:
            raise('missing config entry for environment: %s' % environment)
        return config        
        
    
class Item(db.Model):
    ''' anything a player can own
    '''
    images_path = '/images/items'
    item_name = db.StringProperty(required=True)
    description = db.StringProperty(default=None)
    image_file_name = db.StringProperty(required=True) #doesn't include _l or _s for large/small images
    image_file_extension = db.StringProperty()#required=True)
    purchase_price_coins = db.IntegerProperty() #None = can't buy with coins
    return_price_coins = db.IntegerProperty()
    purchase_price_bucks = db.IntegerProperty() #None = can't buy with bucks
    minimum_experience_level = db.IntegerProperty(default=0)
    large_image_width = db.IntegerProperty(required=True)
    large_image_height = db.IntegerProperty(required=True)
    displayable = db.BooleanProperty() # can be displayed in chamber
    abundance = db.IntegerProperty() # 1-100? chance of being added into a dig square
    
    def get_small_image_path(self):
        return '%s/%s_s.%s' % (self.images_path, self.image_file_name, self.image_file_extension)
    
    def get_large_image_path(self):
        return '%s/%s_l.%s' % (self.images_path, self.image_file_name, self.image_file_extension)
        
class Inventory_item(db.Model):
    ''' item of a player being displayed in chamber
        no key_name, use generated id
    '''
    character = db.ReferenceProperty(Character, required=True)
    item = db.ReferenceProperty(Item, required=True)
    position_x = db.IntegerProperty(required=True)
    position_y = db.IntegerProperty(required=True)
    
class Hunt_trap(db.Model):
    trap_name  = db.StringProperty(required=True)

class Hunt_square(db.Model):
    ''' a single square in the dig area
    '''
    position_x = db.IntegerProperty(required=True) #position in grid
    position_y = db.IntegerProperty(required=True)
    covered = db.BooleanProperty(default=True) # item (if any) is covered by dirt, hidden from view
    item = db.ReferenceProperty(Item, default=None)
    trap = db.ReferenceProperty(Hunt_trap, default=None)
    
    def pixel_pos_x(self):
        return self.position_x * 60

    def pixel_pos_y(self):
        return self.position_y * 60
    
class Hunt_grid(db.Model):
#    character = db.ReferenceProperty(Character, required=True)
    horizontal_size = db.IntegerProperty(required=True)
    vertical_size = db.IntegerProperty(required=True)
    population_time = db.DateTimeProperty()
    #squares = db.ListProperty(db.Key, required=True)

    def get_squares(self):
        query = Hunt_square.all().ancestor(self).order('position_x').order('position_y')
        squares = query.fetch(1000)
        if len(squares) != self.horizontal_size * self.vertical_size:
            logging.warning('grid size for grid with key name %d did not match square count' % self.key().name())
        return squares

    def populate(self):
        
        #if not hunt_grid:
        #    raise Exception('populate_hunt_grid requires valid hunt_grid parameter')

        def fill_squares(hunt_grid, items):
            squares = hunt_grid.get_squares()
            iter_squares = iter(squares)
            update_entities = []
            for x in  range(0, hunt_grid.horizontal_size):
                for y in range(0, hunt_grid.vertical_size):
                    square = iter_squares.next()
                    square.covered = True
                    square.trap = None
                    if square.position_x != x or square.position_y != y:
                        raise Exception('failed to load dig grid squares X was: %d, expected %d.  Y was %d, expected %d' % (square.position_x, x, square.position_y, y))
                    item_dice = random.randint(1, 100)
                    if item_dice > 70: #95:
                        rand_item = random.randint(0, len(items) - 1)
                        square.item = items[rand_item]
                    else:
                        square.item = None
                    update_entities.append(square)
            hunt_grid.population_time = datetime.utcnow()

            query = Hunt_zone_user_status.all().ancestor(hunt_grid.parent())
            dig_zone_statuses = query.fetch(1000)
            db.delete(dig_zone_statuses)
            
            update_entities.append(hunt_grid)
            db.put(update_entities)
            return True
        
        query = Item.all().filter('abundance >',0)
        items = query.fetch(1000)
        db.run_in_transaction(fill_squares, self, items)
        
    @staticmethod
    def create(config, character):
        
        def create_grid_with_squares(config, character):
            hunt_grid = Hunt_grid(parent=character,
                                key_name=character.key().name(),
                                horizontal_size=config.hunt_grid_horizontal_squares,
                                vertical_size=config.hunt_grid_vertical_squares,
                                population_time = datetime.utcnow(),
                                squares = []
                                )
            hunt_grid.put()
            for x in  range(0, hunt_grid.horizontal_size):
                for y in range(0, hunt_grid.vertical_size):
                    key_name = '%s_%s_%s' % (hunt_grid.key().name(), x, y)
                    square = Hunt_square(parent=hunt_grid,
                                        key_name=key_name,
                                        position_x = x,
                                        position_y = y,
                                        covered=True)
                    square.put()
            return hunt_grid
        #hunt_grid = db.run_in_transaction(create_grid_with_squares, config, character)
        hunt_grid = create_grid_with_squares(config, character) #we're already in a transaction.  todo: Can this be detected in code?
        
        return hunt_grid


class Hunt_zone_user_status(db.Model):
    chamber_character = db.ReferenceProperty(Character, required=True, collection_name="hunt_zone_chamber_character_set")
    digging_character = db.ReferenceProperty(Character, required=True, collection_name="hunt_zone_digging_character_set")
    air_level = db.IntegerProperty(required=True)
    updated = db.DateTimeProperty(required=True)
    
