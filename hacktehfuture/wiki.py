import cgi 

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class Wiki(webapp.RequestHandler):
    def get(self):
        self.redirect("http://sites.google.com/a/hackthefuture.org/wiki/")

application = webapp.WSGIApplication([('/wiki', Wiki)], debug=False)


def main():
    run_wsgi_app(application)
