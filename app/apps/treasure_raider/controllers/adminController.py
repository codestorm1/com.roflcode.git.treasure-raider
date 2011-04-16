from google.appengine.ext import db

import logging

class AdminController(object):
    
    def delete_all_entities(self, kind, where_clause=''):
        logging.info('deleting entities of kind %s' % kind)
        q = db.GqlQuery("SELECT __key__ FROM " + kind + where_clause)
        while q.count():
            results = q.fetch(100)
            db.delete(results)
            q = db.GqlQuery("SELECT __key__ FROM " + kind + where_clause)
                    
