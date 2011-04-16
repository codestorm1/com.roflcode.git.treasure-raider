import logging
import md5
import re

#from google.appengine.api.labs import taskqueue
from google.appengine.ext import db # for inventory item deletes only, can remove later

from django.http import HttpResponse
#from django.http import HttpRequest
#from django.template import Template, Context
#from django.template.loader import get_template
from django.shortcuts import render_to_response

from datetime import datetime
from datetime import timedelta

import simplejson

from pyramid.main.accountController import AccountController
from pyramid.main.characterController import CharacterController
from pyramid.main.friends_controller import Friends_controller
from pyramid.main.pyramidController import PyramidController
from pyramid.main.chamberController import ChamberController
from pyramid.main.adminController import AdminController

from pyramid.main.models import Character
from pyramid.main.models import Container_user
from pyramid.main.models import Pyramid
from pyramid.main.models import Positions
from pyramid.main.models import Pyramid_display 
from pyramid.main.models import Offerpal_deposit
from pyramid.main.models import Account
from pyramid.main.models import Message #move message creation to controller
from pyramid.main.models import Experience_limits
from pyramid.main.models import Config

from pyramid.main.models import Item
from pyramid.main.models import Inventory_item

from django.core.paginator import Paginator, InvalidPage, EmptyPage


def format_message_js(title, body):
    return 'addToMessagePopupQueue("%s", "%s");\n' % (title, body)    

def main(request, caller_context, container_user, page=1):
    
    pyramidController = PyramidController()
    chamberController = ChamberController()
    characterController = CharacterController()
    
    current_time = datetime.utcnow() - timedelta(hours = 7) #show Pac time to see if this page gets cached

    if not container_user:
        #user isn't logged in, show some open pyramids
        pyramid_ids = pyramidController.find_open_pyramid_ids(None, 1000)
        if len(pyramid_ids) < 10: # if there are fewer than 10 open pyramids, create one 
            pyramid = pyramidController.create_new_pyramid(4, 3, 100) # 4 total levels, fill 3 levels, $100 price
            pyramid_ids.append(pyramid.key().id())
            logging.debug('created new pyramid: ' + pyramid.to_xml())
        if pyramid_ids:
            pyramid_display, paginator, pyramid_page = get_paged_pyramids(caller_context.config, pyramid_ids, container_user)
        group = 'open'
        return render_to_response('_main.html', locals())

    if caller_context.platform == 'myspace_iframe':
        logging.debug('getting friends from container')
        friends_controller = Friends_controller()
        viewer_friends = friends_controller.refresh_container_friends(container_user)
        encoder = simplejson.JSONEncoder()
        viewer_friends_json = encoder.encode(viewer_friends)

    pyramid_ids = None
    if container_user.character:
        status_bar_dict = characterController.get_status_bar_dict(caller_context.config, container_user.character)
        pyramid_ids = pyramidController.get_character_pyramid_ids(container_user.character, True)
        if pyramid_ids:
            pyramid_display, paginator, pyramid_page = get_paged_pyramids(caller_context.config, pyramid_ids, container_user)
            group = 'joined'
            return render_to_response('_main.html', locals())

    # do this here?  refresh friends?
    #saved, failed = friends_controller.save_container_friends(container_user, viewer_friends)
    #friend_pyramid_ids = pyramidController.get_friend_pyramid_ids(container_user.character, True)

    pyramid_ids = pyramidController.find_open_pyramid_ids(None, 200)
    if pyramid_ids:
        pyramid_display, paginator, pyramid_page = get_paged_pyramids(caller_context.config, pyramid_ids, container_user)
    group = 'open'
    return render_to_response('_main.html', locals())

def get_client_actions(request, caller_context, container_user):
    actions = {}
    
    #make sure we have a character
    if not container_user.character:
        actions['promptForCharacter'] = container_user.display_name
        return json_response(caller_context, container_user, actions, False)

    # check for daily gold bonus
    characterController = CharacterController()
    daily_gold = characterController.check_daily_reward(container_user)
    if daily_gold > 0:
        actions['dailyGold'] = daily_gold

    # get invites
    pyramidController = PyramidController()
    invited_pyramid_ids, invites = pyramidController.get_invited_pyramid_ids(container_user, True)
    if invites:
        actions['invites'] = {}
        for invite in invites:
            actions['invites'][invite.key().name()] = { "character_name" : invite.inviter_character.character_name, 
                                                        "inviterUrl" : invite.inviter_character.image_url }
            #startupJs += 'addToInviteQueue("%s", "%s", "%s");\n' % (invite.key().name(), invite.inviter_character.character_name, invite.inviter_character.image_url)
            
    # check for messages to player
    popup_messages = characterController.get_messages(container_user.character, 20, popup=True, unread=True)
    if popup_messages:
        actions['messages'] = {}
        for message in popup_messages:
            actions['messages'][message.key().name()] = { "title": message.title, 
                                                          "body" : message.body}
    characterController.mark_messages_read(popup_messages) # messages may not have actually been read, this would be better if confirmed via ajax callback
    
    if container_user.character.tutorial_on:
        actions["showTutorial"] = True

    include_experience_data = True
    return json_response(caller_context, container_user, actions, include_experience_data)

def pyramids(request, caller_context, container_user, group, active_page=1, active_position=1):
    '''
    get page of pyramid by taking a pyramid id and finding its page
    '''
    pyramidController = PyramidController()
    pyramid_ids = None
    if (group == "joined"):
        pyramid_ids = pyramidController.get_character_pyramid_ids(container_user.character, True)
    elif (group == "friends"):
        pyramid_ids = pyramidController.get_friend_pyramid_ids(container_user.character, True)
    elif (group == "invited"):
        pyramid_ids, invites = pyramidController.get_invited_pyramid_ids(container_user, True)
    elif (group == "open"):
        character = None
        if container_user:
            character = container_user.character
        pyramid_ids = pyramidController.find_open_pyramid_ids(character, 1000)
        if len(pyramid_ids) < 10: # if there are fewer than 10 open pyramids, create one 
            pyramid = pyramidController.create_new_pyramid(4, 3, 100) # 4 total levels, fill 3 levels, $100 price
            pyramid_ids.append(pyramid.key().id())
            logging.debug('created new pyramid: ' + pyramid.to_xml())
        else:
            logging.debug('found open pyramids')
        #controller.set_game_invite(pyramid, container_user.character)
    elif (group == 'condemned'):
        pyramid_ids = pyramidController.get_character_pyramid_ids(container_user.character, active=False, paid=False)
        
    if pyramid_ids:
        pyramid_display, paginator, pyramid_page = get_paged_pyramids(caller_context.config, pyramid_ids, container_user, 10, int(active_page), int(active_position))

    return render_to_response('pyramids.html', locals())

def status_bar(request, caller_context, container_user):
    ''' for debugging only, but not too useful without CSS
    '''
    return render_to_response('status_bar.html', locals())


def get_paged_pyramids(config, pyramid_ids, container_user, page_size=10, active_page=1, active_position=1):
    ''' move to controller
    '''
    pyramidController = PyramidController()
    paginator = Paginator(pyramid_ids, page_size) 
    pyramid_display = Pyramid_display()

    try:
        pyramid_page = paginator.page(active_page)
    except (EmptyPage, InvalidPage):
        pyramid_page = paginator.page(1)

    pyramid_display.active_pyramid_position = active_position
    pyramid_display.page_size = page_size
    index = 1
    pyramid_display.positions = []
    for position in range(pyramid_page.start_index(), pyramid_page.end_index() + 1):
        positions = Positions()
        positions.position_abs = position
        positions.position_rel = index
        pyramid_display.positions.append(positions)
        index += 1

    if len(pyramid_ids) > 0:
        pyramid_id = pyramid_ids[page_size * (active_page - 1) + active_position - 1]
        pyramid_display.pyramid = Pyramid.get_by_id(pyramid_id)
        if pyramid_display.pyramid == None:
            raise RuntimeError('supplied pyramid_id %d was not found in the data store' % (pyramid_id))
        pyramid_display.bricks = pyramidController.get_bricks_from_pyramid(pyramid_display.pyramid)
        pyramid_display.brick_ids = []
        expired, expire_text = pyramid_display.pyramid.get_expire_text(config.pyramid_lifetime_hours)
        if expired:
            pyramid_display.expire_time_text = 'Expired %s ago' % expire_text
        else:
            pyramid_display.expire_time_text = '%s left to split' % expire_text
#        brick_display_left_pos = (320, 
#                                  165, 439, 
#                                  127, 267, 398, 538, 
#                                  61, 142, 224, 305, 386, 469, 550, 631,)

        brick_display_left_pos = (320, 
                                  264, 378, 
                                  181, 278, 376, 473, 
                                  76, 154, 232, 310, 388, 466, 544, 622,)

        pyramid_display.viewer_brick_descriptions = [];
        for brick in pyramid_display.bricks:
            pyramid_display.brick_ids.append(brick.key().id())
            if brick.character and container_user and container_user.character == brick.character and brick.brick_description:
                pyramid_display.viewer_brick_descriptions.append(brick.brick_description)
            brick.left_pos = brick_display_left_pos[brick.position_in_pyramid - 1]
            
        encoder = simplejson.JSONEncoder()
        pyramid_display.viewer_brick_description_json = encoder.encode(pyramid_display.viewer_brick_descriptions)

    if container_user and container_user.character and container_user.character.key() in pyramid_display.pyramid.character_keys:
        pyramid_display.viewer_in_pyramid = True
    
    return pyramid_display, paginator, pyramid_page

def json_response(caller_context, container_user, return_object, include_experience_data):
    ''' adds experience data for status bar to a json response
    '''
    if include_experience_data:
        characterController = CharacterController()
        status_bar_dict = characterController.get_status_bar_dict(caller_context.config, container_user.character) #refresh experience, gold etc
        return_object['experienceData'] = status_bar_dict
        
    encoder = simplejson.JSONEncoder()
    json = encoder.encode(return_object)
    return HttpResponse(json, 'application/json')
    
def join(request, caller_context, container_user, join_pyramid_id=None, join_brick_id=None, join_invite_key_name=None, action=None):
    ''' data only call, json response
    '''
    pyramidController = PyramidController()
    
    if join_invite_key_name:
        if action == 'accept':
            joinResult, joinInfo  = pyramidController.join_from_invite(caller_context.config, container_user, join_invite_key_name)
        elif action == 'decline':
            joinResult, joinInfo = pyramidController.decline_invite(container_user, join_invite_key_name)
    else:    
        joinResult, joinInfo  = pyramidController.join_pyramid(caller_context.config, int(join_pyramid_id), int(join_brick_id), container_user.character)
    
    joinResponse = { 'success' : joinResult, 
                      'result' : joinInfo}
    
    include_experience_data = False
    if joinResult:
        characterController = CharacterController()
        characterController.add_character_reward(container_user.character, "brick join", 'experience', 75)
        include_experience_data = True
    
    return json_response(caller_context, container_user, joinResponse, include_experience_data)

def cover_square(request, caller_context, container_user, chamber_character_name, grid_pos_x, grid_pos_y):
    ''' data only call, json response
    '''
    chamberController = ChamberController()
    chamber_character = Character.get_by_key_name(chamber_character_name)
    if not chamber_character:
        raise Exception('chamber owner character not found')
    
    uncover_square_result, info = chamberController.cover_dig_square(caller_context.config, container_user, chamber_character, int(grid_pos_x), int(grid_pos_y))
    
    if uncover_square_result:
        square = info # if success, info contains the item to return
        response_square = {
                             'gridPosX' : square.position_x,
                             'gridPosY' : square.position_y
                          }
        response =  { 'success' : True,
                      'square' : response_square
                    }
    else:
        response = { 'success' : False,
                     'reason' : info
                   }

    include_experience_data = False
    return json_response(caller_context, container_user, response, include_experience_data)

def uncover_square(request, caller_context, container_user, chamber_character_name, grid_pos_x, grid_pos_y):
    ''' data only call, json response
    '''
    chamberController = ChamberController()
    chamber_character = Character.get_by_key_name(chamber_character_name)
    if not chamber_character:
        raise Exception('chamber owner character not found')
    
    uncover_square_result, info, air_level = chamberController.uncover_dig_square(caller_context.config, container_user, chamber_character, int(grid_pos_x), int(grid_pos_y))
    
    if uncover_square_result:
        square = info # if success, info contains the item to return
        response_square = {
                             'gridPosX' : square.position_x,
                             'gridPosY' : square.position_y,
                          }
        if square.item:
            response_square['item'] = { 
                                 'itemName' : square.item.item_name,
                                 'description' : square.item.description,
                                 'smallImageUrl' : caller_context.static_root + square.item.get_small_image_path(),
                                 'largeImageUrl' : caller_context.static_root + square.item.get_large_image_path()
                                 }
        else:
            response_square['item'] = None
        response =  { 'success' : True,
                      'airLevel' : air_level,
                      'square' : response_square
                    }
    else:
        response = { 'success' : False,
                     'reason' : info
                   }

    include_experience_data = False
    if uncover_square_result and square.item:
        characterController = CharacterController()
        characterController.add_character_reward(container_user.character, "found grid treasure", 'experience', 75)
        include_experience_data = True
        
    return json_response(caller_context, container_user, response, include_experience_data)

def record_invites(request, caller_context, container_user, brick_description=None):
    ''' data only call, json response
    '''
    
    if request.method != 'POST':
        return HttpResponse('only POST method is supported', 'text/plain')
    invitees = request.POST
    if not brick_description or brick_description == 'null':
        raise RuntimeError('no brick_description supplied for record_invites')
    logging.info('invitees: %s' % invitees)
    characterController = CharacterController()
    characterController.record_sent_invites(container_user, invitees, brick_description)
    response = {"success" : True }
    return json_response(caller_context, container_user, response, False)

def assign_character(request, caller_context, container_user):
    ''' data only call, json response
    '''
    
    characterController = CharacterController()
    logging.info('request is: %s' % request)
    if container_user.character:
        json = '{ "success" : true, "message" : "character already assign to this user" }'
        return HttpResponse(json)
    if not 'character_name' in request.REQUEST:
        json = '{ "success" : false, "message" : "Missing required field \'character_name\'" }'
        return HttpResponse(json)
    character_name = request.REQUEST['character_name'].strip()
    character_name = characterController.unquote_u(character_name)
    character_name = re.sub(r'[\'\"<>`]', ' ', character_name)

    character = Character.get_by_key_name(character_name)
    if character:
        container_users = characterController.get_character_users(character)
        if len(container_users):
            # no other container_user has this character, was probably an error in assignment for this user, so assign it now
            container_user.character = character 
            json = '{ "success" : true, "message" : "Found existing character and assigned it to user" }'
            return HttpResponse(json)
        json = '{ "success" : false, "message" : "Character name is already in use" }'
        return HttpResponse(json)
    character = characterController.create_character(caller_context.config, character_name, container_user.profile_image_url, is_fake=False)
    container_user.character = character
    container_user.put()
    response = { "success" : True, 
                 "message" : "Successfully associated character to container user" }
    return json_response(caller_context, container_user, response, False)

def acknowledge_experience_level(request, caller_context, container_user, level):
    experience_level = int(level)
    response = { 'success' : False,
                'message' : 'incorrect experience level'}
    if experience_level >= container_user.character.acknowledged_experience_level:
        response['success'] = True
        response['message'] = 'experience level acknowledged'
        
        container_user.character.acknowledged_experience_level = experience_level
        container_user.character.put()

    return json_response(caller_context, container_user, response, False)

def update_friends(request, caller_context, container_user):
    
    response = { 'success' : False,
                'message' : 'unknown error'}
    if request.method != "POST":
        response.message ='only POST method is supported'
    else:    
        friends_controller = Friends_controller()
        friends_json = request.raw_post_data
        logging.debug('friends json from update_friends: %s' % friends_json)
        decoder = simplejson.JSONDecoder()
        friends = decoder.decode(friends_json)
        try:
            pyramidController = PyramidController()
            saved, failed = friends_controller.save_container_friends(container_user, friends)
            friend_pyramid_ids = pyramidController.get_friend_pyramid_ids(container_user.character, True)
            response['success'] = True
            response['message'] = 'friend list updated - %d saved, %d failed to save' % (saved, failed) 
            response['friendPyramidCount'] = len(friend_pyramid_ids)
        except Exception, e:
            logging.warn('failed to save friends')
            logging.warn('friends json: %s' % friends_json)
            logging.exception(e)
            response['success'] = False
            response['message'] = 'error saving friends'

    return json_response(caller_context, container_user, response, False)

def user_settings(request, caller_context, container_user, setting, value):
    ''' data only call, json response
    '''
    
    logging.info('request is: %s' % request)

    if not container_user.character:
        response = { "success" : False,
                     "message" : "user is not logged in or has not been assigned a character" }
        return json_response(caller_context, container_user, response, False)
    
    if value == 'on':
        container_user.character.tutorial_on = True
    else:
        container_user.character.tutorial_on = False
    
    container_user.character.put()
    
    response = { "success" : True,
                 "message" : "Successfully updated setting" }

    return json_response(caller_context, container_user, response, False)

def chamber(request, caller_context, container_user, chamber_character_name=None):
    chamberController = ChamberController()
    if chamber_character_name:
        chamber_character = Character.get_by_key_name(chamber_character_name)
    else:
        chamber_character = container_user.character

    viewer_owns_chamber = False
    if chamber_character.key() == container_user.character.key():
        viewer_owns_chamber = True

    chamber_display = chamberController.get_chamber_display(caller_context.config, container_user.character, chamber_character)
    return render_to_response('chamber.html', locals())

def messages(request, caller_context, container_user, page=1):
    characterController = CharacterController()
    messages = characterController.get_messages(container_user.character, 30)
    return render_to_response('messages.html', locals())

def delete_entities(request, caller_context, container_user, kind=None):
    if kind:
        adminController = AdminController()
        if kind == 'all':
            adminController.delete_all_entities('main_container_user')
            logging.debug('wiping main container users')
            adminController.delete_all_entities('pyramid_pyramid')
            logging.debug('wiping pyramids')
            adminController.delete_all_entities('pyramid_brick')
            logging.debug('wiping bricks')
            adminController.delete_all_entities('main_account')
            logging.debug('wiping accounts')
            adminController.delete_all_entities('main_daily_reward')
            logging.debug('wiping rewards')
            adminController.delete_all_entities('main_account_transfer')
            logging.debug('wiping transfers')
            adminController.delete_all_entities('main_join_action')
            logging.debug('wiping join actions')
            adminController.delete_all_entities('main_character', ' where is_fake=False')
            logging.debug('wiping characters')
            adminController.delete_all_entities('main_player_invite')
            logging.debug('wiping player invites')
            adminController.delete_all_entities('main_reward_entry')
            logging.debug('wiping reward entries')
            adminController.delete_all_entities('main_inventory_item')
            logging.debug('wiping reward entries')

            return HttpResponse('weeeeeeee!', 'text/html')
        elif kind == 'most':
            adminController.delete_all_entities('main_container_user')
            adminController.delete_all_entities('pyramid_pyramid')
            adminController.delete_all_entities('pyramid_brick')
            adminController.delete_all_entities('main_character', ' where is_fake=False')
            adminController.delete_all_entities('main_player_invite')
            return HttpResponse('weeeeeeee!', 'text/html')
        else:
            adminController.delete_all_entities(kind)
            return HttpResponse('weee!', 'text/html')
    return HttpResponse('nothing to wipe', 'text/html')

def offerpal_reward(request, caller_context, container_user, container):

    logging.info('offerpal deposit request: %s' % request)
    accountController = AccountController()

    required_fields = ('id', 'snuid', 'currency', 'verifier')
    for field in required_fields:
        if field not in request.GET:
            return HttpResponse(status=400, content='Missing required field: %s' % field)
    offerpal_secret_keys = {'orkut.com' : '1174959640013506'}
    offerpal_id = request.GET['id']
    snuid = request.GET['snuid']
    amount = int(request.GET['currency'])
    verifier = request.GET['verifier']
    affl = None
    if 'affl' in request.GET:
        affl = request.GET['affl'] #optional tracking id
    error = None
    if 'error' in request.GET:
        error = request.GET['error']
    base_string = '%s:%s:%d:%s' % (offerpal_id, snuid, amount, offerpal_secret_keys[container])
    match_string = md5.new(base_string).hexdigest()
    success = False
    found_user = None

    deposit = None
    try:
        deposit = Offerpal_deposit.get_by_key_name(offerpal_id)
    except:
        pass
    if deposit and deposit.success:
        logging.info('duplicate request %s' % deposit.offerpal_id)
        response = HttpResponse('Duplicate request, already received id: %s' % offerpal_id)
        response.status_code = 403 # 403 tells offerpal not to try again
        return response
    
    if match_string != verifier:
        logging.info('base: %s match: %s verifier: %s' % (base_string, match_string, verifier))
        verified = False
        response = HttpResponse('Authorization Failed.')
        response.status_code = 401
    else:
        verified = True
        domain = container             
        container_user_key = domain + ":" + snuid;
        container_user = Container_user.get_by_key_name(container_user_key)
        if container_user == None:
            response = HttpResponse('User Not Found')
            logging.info('could not look up user %s' % container_user_key)
            found_user = False
            response.status_code = 403 # 403 tells offerpal not to try again
            #todo: log this! send email?
        else:
            # log increase, message container_user, notification to container_user
            response = HttpResponse('offerpal reward for %s user.  Reward: %d.' % (container, amount), 'text/html')
            success = True
            found_user = True

    offerpal_deposit = Offerpal_deposit(key_name = offerpal_id,
                                            offerpal_id = offerpal_id, 
                                            snuid = snuid,
                                            currency_type = 'gold',
                                            deposit_amount = amount,
                                            verifier = verifier,
                                            verified = verified,
                                            found_user = found_user,
                                            affl = affl,
                                            error = error,
                                            response_code = response.status_code,
                                            success = success)
    offerpal_deposit.put()
    gold_account = Account(parent=offerpal_deposit,
                           key_name=offerpal_id,
                           currency_type='gold', 
                           negative_balance_allowed=False, 
                           balance=amount)
    gold_account.put()
    offerpal_deposit.account = gold_account
    offerpal_deposit.put()
    
    transfer = accountController.transfer_currency_in_txn(offerpal_deposit.account, container_user.character.gold_account, amount)
    if transfer:
        try:
            message = Message(message_type=5,
                              recipient=container_user.character, 
                              body="Your Offerpal deposit has posted! You have been credited with %d gold pieces" % amount,
                              pop_message_box = True)
            
            message.put() # notify depositor
            accountController.roll_forward_account_transfer(transfer)

        except Exception, e:
            logging.exception(e)
            logging.warning('failed to roll forward transfer of Offerpal deposit')
    return response

def complete_uncommitted_actions(request, caller_context, container_user):
    accountController = AccountController()
    success = True
    try:
        transfer_count = accountController.execute_uncommitted_account_transfers(20)
    except Exception, e:
        success = False
        logging.error(e)
        
    try:
        pyramidController = PyramidController()
        join_count = pyramidController.execute_uncommitted_join_actions(20)
    except Exception, e:
        success = False
        logging.error(e)
    if success:
        return HttpResponse('rolled forward %d gold transfers and %d join actions' % (transfer_count, join_count))
    else:
        response = HttpResponse('exception completing uncommitted actions', status=500)
        return response
        
def expire_pyramids(request, caller_context, container_user):
    pyramidController = PyramidController()
    expired_count, warning_count = pyramidController.handle_expiring_pyramids(caller_context.config)
    if expired_count == 0 and warning_count == 0:
        return HttpResponse('nothing expired', 'text/html')
    else:
        return HttpResponse('expired %d pyramids, warned %d players about expiring pyramids' % (expired_count, warning_count), 'text/html')

#def add_property_single(request, caller_context, container_user, kind, object_key, property_name, property_value):
#    ''' add property to given object
#    '''
#
#    def txn(transform_info):
#        logging.info('modifying entities of kind %s' % kind)
#        q = db.GqlQuery("SELECT __key__ FROM " + transform_info['kind']) # + where_clause)
#        while q.count():
#            results = q.fetch(100)
#            
#            #db.delete(results)
#            q = db.GqlQuery("SELECT __key__ FROM " + transform_info['kind']) # + where_clause)
#
#        
#        counter = Counter.get_by_key_name(key)
#        if counter is None:
#            counter = Counter(key_name=key, count=1)
#        else:
#            counter.count += 1
#        counter.put()
#    transform_info = { 'kind' : kind,
#                      'key' : object_key,
#                      'property_name' : property_name,
#                      'property_value' : property_value }
#    
#    db.run_in_transaction(txn, transform_info)
#
#    key = self.request.get('key')
#
#    # Add the task to the default queue.
#    taskqueue.add(url='/worker', params={'key': key})
#
#    self.redirect('/')
#
##class CounterWorker(webapp.RequestHandler):
##    def post(self): # should run at most 1/s
#def add_property_all(request, caller_context, container_user, kind, property_name, property_value):
#    ''' add property to all existing objects of given kind
#    '''
#    pass
#    

def help(request, caller_context, container_user):
    ''' live
    '''
    chamberController = ChamberController()
    grid = container_user.character.get_hunt_grid()
    chamberController.populate_hunt_grid(grid)     #todo remove this, TESTING ONLY
    
    query = Inventory_item.all().ancestor(container_user.character)
    query.filter('position_y >', 0) # only pull items that are on display
    query.order('position_y').order('position_x')
    display_items = query.fetch(1000)
    
    db.delete(display_items)
    
    return render_to_response('help.html', locals())

def how_to_play(request, caller_context, container_user):
    return render_to_response('how_to_play.html', locals())

def action_items(request, caller_context, container_user):
    return render_to_response('action_items.html', locals())

def get_more_gold(request, caller_context, container_user):
    return render_to_response('get_more_gold.html', locals())

def quick_start(request, caller_context, container_user):
    return render_to_response('quick_start.html', locals())

def inventory(request, caller_context, container_user):
    return render_to_response('inventory.html', locals())

def about(request, caller_context, container_user):
    return render_to_response('about.html', locals())

def admin_brick_table(request, caller_context, container_user):
    return render_to_response('admin_brick_table.html', locals())

def scratch(request, caller_context, container_user):
    
    config = Config(key_name='test',
                experience_limits_group = 'test',
                starting_gold = 5000,
                starting_pharaoh_bucks = 3,
                pyramid_lifetime_hours = 168,
                pyramid_warning_hours = 72,
                starting_active_bricks = 3,
                hunt_grid_horizontal_squares = 10,
                hunt_grid_vertical_squares = 5,
                dig_zone_air_capacity = 5,
                dig_zone_air_replenish_hours = 8)
    config.put()
    config = Config(key_name='prod',
                experience_limits_group = 'normal',
                starting_gold = 500,
                starting_pharaoh_bucks = 3,
                pyramid_lifetime_hours = 168,
                pyramid_warning_hours = 72,
                starting_active_bricks = 3,
                hunt_grid_horizontal_squares = 10,
                hunt_grid_vertical_squares = 5,
                dig_zone_air_capacity = 5,
                dig_zone_air_replenish_hours = 8)
    config.put()

    response = HttpResponse('scratch executed', 'text/html')
    return response

    key_name = 'Lotus Chalice'
    item = Item(key_name=key_name,
    item_name = key_name,
    image_file_name = 'lotus_chalice',
    image_file_extension = 'png',
    purchase_price_coins = 100,
    return_price_coins = 20,
    purchase_price_bucks = None,
    minimum_experience_level = None,
    large_image_width = 57,
    large_image_height = 109,
    abundance = 50)
    item.put()

    key_name = 'Cartouche'
    item = Item(key_name=key_name,
    item_name = key_name,
    image_file_name = 'cartouche',
    image_file_extension = 'png',
    purchase_price_coins = 100,
    return_price_coins = 20,
    purchase_price_bucks = None,
    minimum_experience_level = None,
    large_image_width = 69,
    large_image_height = 118,
    abundance = 25)
    item.put()

    key_name = 'Fancy Ankh'
    item = Item(key_name=key_name,
    item_name = key_name,
    image_file_name = 'fancy_ankh',
    image_file_extension = 'png',
    purchase_price_coins = 100,
    return_price_coins = 20,
    purchase_price_bucks = None,
    minimum_experience_level = None,
    large_image_width = 61,
    large_image_height = 117,
    abundance = 25)
    item.put()
    
    response = HttpResponse('scratch executed', 'text/html')
    return response
    
    
    character = container_user.character
    #key_name = 'Fancy Ankh'
    #key_name = 'Cartouche'
    key_name = 'Lotus Chalice'
    item = Item.get_by_key_name(key_name)
    if item:

        #kn = '%s_%s' % (container_user.character.character_name, key_name) 
#        inv = Inventory_item(parent=container_user.character,
#                            key_name=key_name,
#                            item=item,
#                            quantity=1)
#        inv.put()
        invItem = Inventory_item(parent= container_user.character,
                               character = container_user.character,
                               item = item,
                               position_x = 200,
                               position_y = 30)
        invItem.put()
        character.put()
        
        
#class DisplayItem(db.Model):
#    ''' item of a player being displayed in chamber
#        no key_name, use generated id
#    '''
#    character = db.ReferenceProperty(Character, required=True)
#    item = db.ReferenceProperty(Item, required=True)
#    position_x = db.IntegerProperty(required=True)
#    position_y = db.IntegerProperty(required=True)
    
        
    response = HttpResponse('scratch executed', 'text/html')
    return response
