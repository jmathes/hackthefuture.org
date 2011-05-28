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

"""Debug bootstraping code for Eclipse.

This code ensures the environment is set up correctly by adding the library
paths to the environment and then call the dev_appserver's main method.
Intended to be the main module for an Eclipse debugging session.

"""

import os

SDK_PATH = '/usr/local/google_appengine'
os.sys.path.insert(0, '%s/lib/django/' % SDK_PATH)
os.sys.path.insert(0, '%s/lib/webob/' % SDK_PATH)
os.sys.path.insert(0, '%s/lib/yaml/lib/' % SDK_PATH)
os.sys.path.insert(0, '%s/' % SDK_PATH)

import google.appengine.tools.dev_appserver_main
google.appengine.tools.dev_appserver_main.main(os.sys.argv)
