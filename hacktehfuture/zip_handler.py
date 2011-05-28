#!/usr/bin/python2.5
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Code to serve files from zip files located in different locations.

"""

from google.appengine.ext import webapp
from google.appengine.ext import zipserve
from google.appengine.ext.webapp import util

def main():
  """Sets up handlers for the zip files."""
  file_icons = zipserve.make_zip_handler('static/images/fileicons.zip')
  fck_editor = zipserve.make_zip_handler('third_party/fckeditor.zip')
  
  application = webapp.WSGIApplication(
      [('/static/images/fileicons/(.*)', file_icons),
       ('/fckeditor/(.*)', fck_editor),
      ])
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
