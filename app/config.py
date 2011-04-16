# -*- coding: utf-8 -*-
"""
    base_config
    ~~~~~~

    Configuration settings.

    :copyright: 2009 by tipfy.org.
    :license: BSD, see LICENSE for more details.
"""
base_config = {'tipfy': {
    # Enable debugger. It will be loaded only in development.
    'middleware': [
            'tipfy.ext.debugger.DebuggerMiddleware',
            ],
    # Enable the Hello, World! app example.
    'apps_installed': [
            'apps.hello_world',
            'apps.treasure_raider'
    ],
    }, 'tipfy.ext.session': {
    'secret_key': 'BRYANSKEY3498230948234SfsldflkSFSF',
    }, 'tipfy.ext.auth.friendfeed': {
    'consumer_key': 'XXXXXXXXXXXXXXX',
    'consumer_secret': 'XXXXXXXXXXXXXXX',
    }, 'tipfy.ext.auth.twitter': {
    'consumer_key': 'xppPxF9JMjgrBA3VjvmVyQ',
    'consumer_secret': 'EwedoF5dJSo5KHy1rJ6mIqICaKfpEV7x6kKkDIM1w',
    }}

# Configurations for the 'tipfy' module.


configs = {'development': base_config.copy(), 'production': base_config.copy()}

configs['development']['tipfy.ext.auth.facebook'] = {
        'environment' : 'development',
        'app_id': '150520701677303',
        'api_key': '3f2a276f14af70d2ee5d982bacdc2f7a',
        'app_secret': '11bc317fee74d3ccf61ef3bce720315b' #treasure raider Localhost
    }

configs['production']['tipfy.ext.auth.facebook'] = {
        'environment' : 'production',
        'app_id': '171012306285008',
        'api_key': '85298983265d92146c6516cea740bc34', #tr
        'app_secret': '08235e0b2284536c3a6a49491091b723',#tr
    }
