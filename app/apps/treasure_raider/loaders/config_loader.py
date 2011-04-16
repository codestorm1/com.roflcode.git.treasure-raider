from google.appengine.ext import db
from google.appengine.tools import bulkloader

from treasure_raider.models import Config

class Config_loader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'Config',
                               [('key_name', str),
                                ('experience_limits_group', str),
                                ('starting_cash', int),
                                ('starting_coins', int),
                                ('hunt_zone_max_air', int),
                                ('daily_air_refresh_rate', int),
                                ('hunt_grid_horizontal_squares', int),
                                ('hunt_grid_vertical_squares', int),
                                ])

loaders = [Config_loader]

#newline characters may need to be converted with tr command
#tr '\r' '\n' < macfile.txt > unixfile.txt