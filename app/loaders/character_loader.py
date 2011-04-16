import datetime
from google.appengine.ext import db
from google.appengine.tools import bulkloader

class main_character(db.Model):
    character_name = db.StringProperty()
    image_url = db.StringProperty()
    language = db.StringProperty()
    country = db.StringProperty()
    ip_address = db.StringProperty()
    experience = db.IntegerProperty()
    creation_date = db.DateTimeProperty()
    is_fake = db.BooleanProperty(default=True)

class CharacterLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'main_character',
                               [('character_name', str),
                                ('key_name', str),
                                ('image_url', str),
                                ('is_fake', bool),
                                ('creation_date',
                                     lambda x: datetime.datetime.now()) #strptime(x, '%m/%d/%Y').date())
                                ])
                               
loaders = [CharacterLoader]

