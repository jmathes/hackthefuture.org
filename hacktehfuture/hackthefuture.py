import cgi

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write("""

<!DOCTYPE html>
<html>
<head>
	
<title>
Hack The Future Mailing List Signup
</title>

<style type="text/css">
*{margin:0;padding:0;}
html{overflow:hidden;}
#wufoo{position:absolute;width:100%;height:100%;}
body{margin-bottom:-17px;}
iframe{height:100%;width:100%;border:none;}
</style>

</head>

<body>
	
<div id="wufoo">
<iframe title="Hack The Future Mailing List Signup" frameborder="0" src="http://hackthefuture.wufoo.com/forms/z7x3k7/">
<a href="http://hackthefuture.wufoo.com/forms/z7x3k7/" title="HTML form">Fill out my Wufoo form!</a>
</iframe>
</div>

</body>
</html>
""")
#        self.response.out.write("""
#          <html>
#            <body>
#              <form action="/sign" method="post">
#                <div><textarea name="content" rows="3" cols="60"></textarea></div>
#                <div><input type="submit" value="Sign Guestbook"></div>
#              </form>
#            </body>
#          </html>""")


class Guestbook(webapp.RequestHandler):
    def post(self):
        self.response.out.write('<html><body>You wrote:<pre>')
        self.response.out.write(cgi.escape(self.request.get('content')))
        self.response.out.write('</pre></body></html>')

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/sign', Guestbook)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
