# -*- coding: utf-8 -*-
"""
    urls
    ~~~~

    URL definitions.

    :copyright: 2009 by tipfy.org.
    :license: BSD, see LICENSE.txt for more details.
"""
from tipfy import Rule, import_string


def get_rules(app):
    """Returns a list of URL rules for the application. The list can be
    defined entirely here or in separate ``urls.py`` files.

    :param app:
        The WSGI application instance.
    :return:
        A list of class:`tipfy.Rule` instances.
    """

    rules = [
        Rule('/home/', endpoint='home', handler='apps.treasure_raider.handlers.HomeHandler'), #not used
        Rule('/auth/login/', endpoint='auth/login', handler='apps.treasure_raider.handlers.LoginHandler'),
        Rule('/auth/logout/', endpoint='auth/logout', handler='apps.treasure_raider.handlers.LogoutHandler'),
        Rule('/auth/signup/', endpoint='auth/signup', handler='apps.treasure_raider.handlers.SignupHandler'),
        Rule('/auth/register/', endpoint='auth/register', handler='apps.treasure_raider.handlers.RegisterHandler'),
        Rule('/auth/facebook/', endpoint='auth/facebook', handler='apps.treasure_raider.handlers.FacebookAuthHandler'),
        Rule('/auth/facebookclientflow', endpoint='auth/facebookclientflow', handler='apps.treasure_raider.handlers.FacebookClientFlowAuthHandler'),
        Rule('/auth/facebookserverflow', endpoint='auth/facebookserverflow', handler='apps.treasure_raider.handlers.FacebookServerFlowAuthHandler'),
        Rule('/auth/friendfeed/', endpoint='auth/friendfeed', handler='apps.treasure_raider.handlers.FriendFeedAuthHandler'),
        Rule('/auth/google/', endpoint='auth/google', handler='apps.treasure_raider.handlers.GoogleAuthHandler'),
        Rule('/auth/twitter/', endpoint='auth/twitter', handler='apps.treasure_raider.handlers.TwitterAuthHandler'),
        Rule('/auth/yahoo/', endpoint='auth/yahoo', handler='apps.treasure_raider.handlers.YahooAuthHandler'),

        Rule('/', endpoint='content/index', handler='apps.treasure_raider.handlers.ContentHandler'),

        Rule('/canvas/', endpoint='/canvas', handler='apps.treasure_raider.handlers.ExampleHandler'),
        #Rule('/canvas/', endpoint='/canvas', handler='apps.treasure_raider.onsite_handlers.RecentRunsHandler'),
        #Rule('/user/(.*)', endpoint='/user', handler='apps.treasure_raider.onsite_handlers.UserRunsHandler'),
        #Rule('/run', endpoint='/run', handler='apps.treasure_raider.onsite_handlers.RunHandler'),
        #Rule('/realtime', endpoint='/realtime', handler='apps.treasure_raider.onsite_handlers.RealtimeHandler'),

        #Rule('/task/refresh-user/(.*)', endpoint='/task/refresh-user', handler='apps.treasure_raider.onsite_handlers.RefreshUserHandler'),
        #Rule('/', endpoint='/', handler='apps.treasure_raider.onsite_handlers.
    
    ]

    return rules
