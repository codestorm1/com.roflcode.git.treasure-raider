# -*- coding: utf-8 -*-
"""
    main
    ~~~~

    Run Tipfy apps.

    :copyright: 2009 by tipfy.org.
    :license: BSD, see LICENSE for more details.
"""
import os
import sys

if 'lib' not in sys.path:
    # Add /lib as primary libraries directory, with fallback to /distlib
    # and optionally to distlib loaded using zipimport.
    sys.path[0:0] = ['lib', 'distlib', 'distlib.zip']

import config
import tipfy
from google.appengine.dist import use_library

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
use_library('django', '0.96')

# Is this the development server?
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

sys.path.append(os.path.join(os.path.dirname(__file__), 'apps'))

env_config = config.configs['development'] if debug else config.configs['production']



# Instantiate the application.
app = tipfy.make_wsgi_app(config=env_config, debug=debug)


def main():
    app.run()


if __name__ == '__main__':
    main()
