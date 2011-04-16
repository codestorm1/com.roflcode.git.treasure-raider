import logging

from tipfy import abort, cached_property, import_string, redirect
from treasure_raider.models import Config

class EnvironmentMiddleware(object):
    """A RequestHandler middleware decorator to require the current user to
    have an account saved in datastore. This acts as a `user_required`
    decorator but for handler classes. Example:

    .. code-block:: python

       from tipfy import RequestHandler
       from tipfy.ext.auth import AppEngineAuthMixin, UserRequiredMiddleware

       class MyHandler(RequestHandler, AppEngineAuthMixin):
           middleware = [UserRequiredMiddleware]

           def get(self, **kwargs):
               return 'Only users can see this.'
    """
    def pre_dispatch(self, handler):
        return self._populate_environment(handler)
    
    @cached_property
    def get_game_config(self):
        return Config.get_by_key_name('development')        
        
    def _populate_environment(self, handler):
        """Implementation for user_required and UserRequiredMiddleware."""
        
        #todo cache this
        handler.game_config = self.get_game_config
        
def populate_environment(func):
    """A RequestHandler method decorator to require the current user to
    have an account saved in datastore. Example:

    .. code-block:: python

       from tipfy import RequestHandler
       from tipfy.ext.auth import AppEngineAuthMixin, user_required

       class MyHandler(RequestHandler, AppEngineAuthMixin):
           @user_required
           def get(self, **kwargs):
               return 'Only users can see this.'

    :param func:
        The handler method to be decorated.
    :returns:
        The decorated method.
    """
    def decorated(self, *args, **kwargs):
        return _populate_environment(self) or func(self, *args, **kwargs)

    return decorated



#    if not handler.auth_session:
#        return redirect(handler.auth_login_url())
#
#    if not handler.auth_current_user:
#        return redirect(handler.auth_signup_url())


    