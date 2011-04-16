from google.appengine.ext import db

import logging
import random

from datetime import datetime

from pyramid.main.models import Item
from pyramid.main.models import Inventory_item
from pyramid.main.models import Hunt_grid
from pyramid.main.models import Hunt_square
from pyramid.main.models import Hunt_zone_user_status

class ChamberController(object):
    
    def get_chamber_display(self, config, logged_in_character, chamber_character):
        chamber_display = {}
        query = Inventory_item.all().ancestor(chamber_character)
        query.filter('position_y >', 0) # only pull items that are on display
        query.order('position_y').order('position_x')
        display_items = query.fetch(1000)
        chamber_display['display_items'] = display_items
        chamber_display['character'] = chamber_character
        hunt_grid = chamber_character.get_hunt_grid()
        chamber_display['hunt_grid'] = hunt_grid
        key_name = '%s_%s' % (logged_in_character.key().name(), chamber_character.key().name())
        hunt_zone_status = Hunt_zone_user_status.get_by_key_name(key_names = key_name,
                                                               parent = chamber_character)
        if hunt_zone_status:
            elapsed_time = datetime.utcnow() - hunt_zone_status.updated
            total_seconds = (elapsed_time.microseconds + (elapsed_time.seconds + elapsed_time.days *  24 * 3600) * 10**6) / 10**6
            #elapsed_minutes = total_seconds / 60
            elapsed_hours = total_seconds / 3600
            air_per_hour = float(config.hunt_zone_air_capacity) / float(config.hunt_zone_air_replenish_hours)
            new_air = int(elapsed_hours * air_per_hour)
            hunt_zone_status.air_level = new_air + hunt_zone_status.air_level
            if hunt_zone_status.air_level >  config.hunt_zone_air_capacity:
                hunt_zone_status.air_level = config.hunt_zone_air_capacity
        else:
            hunt_zone_status = Hunt_zone_user_status(parent = chamber_character,
                                       key_name = key_name,
                                       chamber_character = chamber_character,
                                       huntging_character = logged_in_character,
                                       air_level = config.hunt_zone_air_capacity,
                                       updated = datetime.utcnow())
        hunt_zone_status.put()
            
        chamber_display['hunt_zone_user_status'] = hunt_zone_status
        return chamber_display

    
    def get_hunt_square(self, chamber_character, grid_pos_x, grid_pos_y):
        hunt_grid = chamber_character.get_hunt_grid()
        key_name = '%s_%s_%s' % (hunt_grid.key().name(), grid_pos_x, grid_pos_y)
        square = Hunt_square.get_by_key_name(key_name, parent = hunt_grid)
        if not square:
            logging.warning('square %s not found' % key_name)
            return False, 'square not found'
        return square, 'success'

    def cover_hunt_square(self, config, container_user, chamber_character, grid_pos_x, grid_pos_y):
        
        if not chamber_character:
            return False, 'chamber character not supplied'
        if container_user.character != chamber_character:
            return False, 'only owner of chamber can fill holes'
        square, reason = self.get_hunt_square(chamber_character, grid_pos_x, grid_pos_y)
        if not square:
            return False, reason
        
        if square.covered:
            logging.debug('square %s already covered')
            return False, 'square was already covered'
        
        square.covered = True
        square.put()
        return True, square
    
    def uncover_hunt_square(self, config, container_user, chamber_character, grid_pos_x, grid_pos_y):
        
        if not chamber_character:
            return False, 'chamber character not supplied', None
        #if container_user.character == chamber_character:
        #    return False, 'owner of chamber cannot hunt holes'
        
        def do_uncover(config, character, chamber_character, grid_pos_x, grid_pos_y):
            
            key_name = '%s_%s' % (character.key().name(), chamber_character.key().name())
            hunt_zone_status = Hunt_zone_user_status.get_by_key_name(parent = chamber_character,
                                                         key_names = key_name)
            if not hunt_zone_status:
                logging.error('no user status found for this hunt zone')
                return False, 'Could not determine air status', None
            if hunt_zone_status.air_level < 1:
                return False, 'Not enough air', None #don't change text without changing JS.  String match.

            square, reason = self.get_hunt_square(chamber_character, grid_pos_x, grid_pos_y)
            if not square:
                return False, reason, None

            if not square.covered:
                logging.debug('square %s already uncovered')
                return True, square, None # return False, 'square was already revealed'
        
            square.covered = False
            hunt_zone_status.air_level -= 1
            hunt_zone_status.updated = datetime.utcnow()
            db.put([square, hunt_zone_status])
            return True, square, hunt_zone_status.air_level
        
        result, square, air_level = db.run_in_transaction(do_uncover, config, container_user.character, chamber_character, grid_pos_x, grid_pos_y)

        if result and square.item:
            x = random.randint(0, 700)
            y = random.randint(0, 80)
            inventory_item = Inventory_item(parent = container_user.character,
                                            character = container_user.character,
                                            item = square.item,
                                            position_x = x,
                                            position_y = y)
            inventory_item.put()
        return result, square, air_level
        # when to move square to user inventory?

