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
        Rule('/', endpoint='home', handler='apps.auth_demo.handlers.HomeHandler'),
        Rule('/auth/login', endpoint='auth/login', handler='apps.auth_demo.handlers.LoginHandler'),
        Rule('/auth/logout', endpoint='auth/logout', handler='apps.auth_demo.handlers.LogoutHandler'),
        Rule('/auth/signup', endpoint='auth/signup', handler='apps.auth_demo.handlers.SignupHandler'),
        Rule('/auth/register', endpoint='auth/register', handler='apps.auth_demo.handlers.RegisterHandler'),

        Rule('/auth/facebook/', endpoint='auth/facebook', handler='apps.auth_demo.handlers.FacebookAuthHandler'),
        Rule('/auth/friendfeed/', endpoint='auth/friendfeed', handler='apps.auth_demo.handlers.FriendFeedAuthHandler'),
        Rule('/auth/google/', endpoint='auth/google', handler='apps.auth_demo.handlers.GoogleAuthHandler'),
        Rule('/auth/twitter/', endpoint='auth/twitter', handler='apps.auth_demo.handlers.TwitterAuthHandler'),
        Rule('/auth/yahoo/', endpoint='auth/yahoo', handler='apps.auth_demo.handlers.YahooAuthHandler'),

        Rule('/content', endpoint='content/index', handler='apps.auth_demo.handlers.ContentHandler'),
    ]

    return rules
