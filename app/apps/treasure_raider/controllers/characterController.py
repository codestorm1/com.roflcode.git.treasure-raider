from google.appengine.ext import db

import logging
import random
import urllib

from datetime import datetime
from datetime import date

from pyramid.main.accountController import AccountController
from pyramid.main.chamberController import ChamberController


from pyramid.main.models import Container_user
from pyramid.main.models import Caller_context
from pyramid.main.models import Account
from pyramid.main.models import Character
from pyramid.main.models import Player_invite
from pyramid.main.models import Message
from pyramid.main.models import Account_transfer
from pyramid.main.models import Daily_reward
from pyramid.main.models import Reward_entry
from pyramid.main.models import Experience_limits


class CharacterController(object):
    

    def get_character_users(self, character):
        ''' find container users of the character
        '''
        query = Container_user.all()
        query.filter('character', character)
        users = query.fetch(1000)
        return users
    
    def get_fake_characters(self, max_characters): 
        # grab some fake players to fill most of the pyramid
        query = Character.all()
        query.filter('is_fake', True)
        fake_characters = query.fetch(max_characters)
        return fake_characters
    
      
    def get_messages(self, character, max_messages, popup=None, unread=False):
        query = Message.all().filter('recipient', character)
        if popup:
            query.filter('pop_message_box', True) #only get messages that need to be shown in popup message box 
        if unread:
            query.filter('read_by_user', False)
        message_list = query.fetch(max_messages)
        return message_list
    
    def mark_messages_read(self, messages):
        for message in messages:
            message.read_by_user = True;
        db.put(messages)
    

    def add_character_reward(self, character, description, currency_type, amount):
        ''' bit of a hack, currency_type can be 'experience' which has no account,
            or pharaoh bucks, which does have an account
        ''' 
        def add_reward(reward_entry):
            logging.info('adding reward type %s, amount %d' % (reward_entry.currency_type, reward_entry.amount))
            #character = Character.get(reward_entry.character.key()) # force transactional reload of character
            # the above read makes the increment transactional, but another reference
            # to this character outside this function was getting saved and clobbered the changes
            if not character:
                logging.warn('no character found in add_experience')
                return False
            if reward_entry.currency_type == 'experience':
                character.experience_points += amount
                db.put((reward_entry, character))
            elif reward_entry.currency_type == 'cash':
                character.cash_account.balance += amount 
                db.put((reward_entry, character.cash_account))
            elif reward_entry.currency_type == 'max_active_bricks':
                character.max_active_bricks += amount 
                db.put((reward_entry, character))
            else:
                raise Exception('unsupported currency type')
            return character
        logging.info('currency: %s' % currency_type)
        reward_entry = Reward_entry(parent=character,
                                            character=character,
                                            description=description,
                                            currency_type=currency_type,
                                            amount=amount)
        logging.info('txn run add_reward entry: %s' % reward_entry)
        character = db.run_in_transaction(add_reward, reward_entry)
    
    def check_daily_reward(self, container_user):
        '''was rewarding experience for daily visit as well as coins.  dropping it for now.
           characterController.add_character_reward(container_user.character, "daily visit", 'experience', 50)
        '''

        accountController = AccountController()
        today = date.today()
        def get_or_create_daily_reward_tx():
            todays_reward = Daily_reward.get_by_key_name(str(today))
            if not todays_reward:
                todays_reward = Daily_reward(key_name=str(today), date=today)
                todays_reward.put()
                coins_account = Account(parent=todays_reward, 
                                       currency_type='coins', 
                                       negative_balance_allowed=True)
                coins_account.put()
                todays_reward.coins_account = coins_account # redundant account again, is this really necessary?
                todays_reward.put()
            return todays_reward
                        
        def pay_daily_reward_tx(reward_account, character_coins_account):
            dest_transfer = Account_transfer.get_by_key_name(str(character_coins_account.key()), parent=reward_account) #str(reward_account.key())
            if not dest_transfer:
                amount = random.randint(25, 75)
                transfer = accountController.transfer_currency(todays_reward.coins_account, character_coins_account, amount)
                return transfer
            return None
            
        todays_reward = db.run_in_transaction(get_or_create_daily_reward_tx)        
        reward_transfer = db.run_in_transaction(pay_daily_reward_tx, todays_reward.coins_account, container_user.character.coins_account)
        if reward_transfer:
            try:
                accountController.roll_forward_account_transfer(reward_transfer)
            except Exception, e:
                logging.exception(e)
            return reward_transfer.amount
        else:
            return 0
        
    def record_sent_invites(self, container_user, invitees, brick_description):
        if not brick_description or brick_description == 'null':
            raise  RuntimeError('no brick_description supplied for record_sent_invites')
        for index in invitees:
#            q = Brick.all().filter('brick_description', brick_description)
#            brick = q.fetch(1) #todo: change to get()?
#            logging.info('brick desc %s' % brick_description)
#            logging.info('brick! %s' % brick)
            key = '%s_%s_%s_%s' % (container_user.domain, container_user.container_user_id, invitees[index], brick_description)
            invite = Player_invite.get_by_key_name(key)
            if invite:
                invite.is_active = True #re-use invite, player sent another from same brick
            else:
                invitee_user_key = '%s:%s' % (container_user.domain, invitees[index])
                invitee_user = Container_user.get_by_key_name(invitee_user_key)
                invitee_character = None
                if invitee_user and invitee_user.character:
                    invitee_character = invitee_user.character
            
                invite = Player_invite(key_name = key,
                                       inviter_container_user = container_user,
                                       inviter_character = container_user.character,  
                                       domain = container_user.domain, 
                                       invitee_container_user_id = invitees[index],
                                       invitee_container_user = invitee_user,
                                       invitee_character = invitee_character,
                                       inviter_brick_description = brick_description,
                                       invitee_bricks = [],
                                       invite_time = datetime.utcnow(),
                                       is_active = True,
                                       invite_successful = None)
            invite.put()

    def unquote_u(self, source):
        result = source
        if '%u' in result:
            result = result.replace('%u','\\u').decode('unicode_escape')
        result = urllib.unquote(result)
        return result

    def get_status_bar_dict(self, config, character):
    
        character, limits = self.load_experience_limits(config, character)
        #should it be in data Model? or calculate?
        
        #limits_key = '%s_%s' % (config.experience_limits_group, character.acknowledged_experience_level)
        #old_limits = Experience_limits.get_by_key_name(limits_key)
        #old_max_bricks = old_limits.max_active_bricks

        status_data = { 'upgradeRewardCash' : limits.cash_reward,
                        'upgradeRewardMaxActiveBricks' : limits.active_brick_reward,
                        'activeBrickCount' : character.active_brick_count,
                        'maxActiveBricks' : character.max_active_bricks,
                        'experienceLevel' : limits.experience_level,
                        'acknowledgedExperienceLevel' : character.acknowledged_experience_level,
                        'experiencePoints' : character.experience_points,
                        'experienceProgress' : character.experience_progress,
                        'cash' : character.cash_account.balance, #character.cash_account.balance,
                        'coins' : character.coins_account.balance}
        return status_data

    def load_experience_limits(self, config, character):
        ''' only persisting experience level on the character.
            then recalculate the level using current experience points
        '''
        
        #todo: this isn't totally reliable, if a level is missed somehow, rewards won't be recovered  
        
        query = Experience_limits.all()
        query.filter('group', config.experience_limits_group)
        query.filter('min_experience_points <=', character.experience_points) 
        query.order('-min_experience_points')
        limits_list = query.fetch(1)

        if len(limits_list) != 1:
            raise Exception('could not load experience limits for user: %s group: %s points: %d' % (character.character_name, config.experience_limits_group, character.experience_points))
        limits = limits_list[0]
        points_til_next_level = limits.next_experience_points - limits.min_experience_points
        character.experience_progress = (character.experience_points - limits.min_experience_points) * 100 / points_til_next_level # percent til next level

        limits.experience_upgraded = False
        logging.warn('character.experience_level %d limits.experience_level: %d' % (character.experience_level, limits.experience_level))
        if character.experience_level < limits.experience_level:
            reward_description = 'promotion to level %d' % limits.experience_level
            self.add_character_reward(character, reward_description, 'cash', limits.cash_reward)
            logging.debug('adding %d max bricks' % limits.active_brick_reward)
            self.add_character_reward(character, reward_description, 'max_active_bricks', limits.active_brick_reward)
            character.experience_level = limits.experience_level
            character.put() # change this to record upgraded level only after user has acknowledged the upgrade
        return character, limits
