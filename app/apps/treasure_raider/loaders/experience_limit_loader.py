from google.appengine.ext import db
from google.appengine.tools import bulkloader


class Experience_limits_loader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'Experience_limits',
                               [('key_name', str),
                                ('group', str),
                                ('experience_level', int),
                                ('min_experience_points', int),
                                ('next_experience_points', int),
                                ('air_capacity_reward', int),
                                ('cash_reward', int),
                                ('coins_reward', int),
                                ])

loaders = [Experience_limits_loader]

#newline characters may need to be converted with tr command
#tr '\r' '\n' < macfile.txt > unixfile.txt