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

"""Utility methods."""

import functools
import logging
import configuration

from django import http
from django import shortcuts
from django.core import urlresolvers
from google.appengine.api import memcache
from google.appengine.api import users
import models


def respond(request, template, params=None):
  """Helper to render a response.

  This function assumes that the user is logged in.

  Args:
    request: The request object
    template: The template name; '.html' is appended automatically.
    params: A dict giving the template parameters; modified in-place.

  Returns:
    Whatever render_to_response(template, params) returns.

  Raises:
    Whatever render_to_response(template, params) raises.

  """
  if params is None:
    params = {}

  if request.user:
    params['user'] = request.user
    params['sign_out'] = users.CreateLogoutURL('/')
    params['is_admin'] = users.is_current_user_admin()
  else:
    params['sign_in'] = users.CreateLoginURL(request.path)

  if hasattr(request, 'profile') and request.profile is not None:
    profile = request.profile
    params['sidebar'] = models.Sidebar.render(profile)
    params['is_superuser'] = profile.is_superuser
  else:
    params['is_superuser'] = False
    params['sidebar'] = models.Sidebar.render(None)
    
  params['configuration'] = configuration

  if not template.endswith('.html'):
    template += '.html'

  return shortcuts.render_to_response(template, params)


def forbidden(request, error_message=None):
  """Returns a 403 response based on a template.

  Args:
    request: the http request that was forbidden
    error_message: a message to display that will override the default message

  Returns:
    A http response with the status code of 403

  """
  response = respond(request, '403', {'error_message': error_message})
  response.status_code = 403
  return response


def page_not_found(request, error_message=None):
  """Returns a 404 response based on a template.

  Args:
    request: the http request that was forbidden
    error_message: a message to display that will override the default message

  Returns:
    A http response with the status code of 404
  """
  response = respond(request, '404', {'error_message': error_message})
  response.status_code = 404
  return response


def edit_updated_page(page_id, message_id='', tab_name=''):
  """Issues a redirect to the edit form for page_id.

  Args:
    page_id: the id of the page that is being edited
    message_id: the id of the message element to be displayed to the user once
                the page is reloaded
    tab_name: the name of the tab to default to when the page is reloaded

  Returns:
    A http redirect to the edit form for page_id

  """
  url = urlresolvers.reverse('views.admin.edit_page', args=[str(page_id)])
  if message_id:
    url = '%s?m=%s' % (url, message_id)
  if tab_name:
    url = '%s#%s' % (url, tab_name)
  return http.HttpResponseRedirect(url)


def memcache_get(key):
  """Gets data from the memcache.

  This method is currently in place to avoid having to disable the pylint
  message across the codebase.

  """
  return memcache.get(key)  # pylint: disable-msg=E1101


def memcache_set(key, val):
  """Sets data in the memcache.

  This method is currently in place to avoid having to disable the pylint
  message across the codebase.

  """
  return memcache.set(key, val)  # pylint: disable-msg=E1101


def clear_memcache():
  """Flushes the memcache when an entry is edited."""
  if not memcache.flush_all():  # pylint: disable-msg=E1101
    logging.error('Failed to clear the cache!')


def flush_cache(func):
  """Decorator to flush the cache."""

  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    data = func(*args, **kwargs)
    logging.info('Flushing the cache')
    _local_cache.clear()
    if not memcache.flush_all():
      logging.error('Memcache flush failed.')
    return data

  return wrapper


def edit_instance(request, model_type, model_form_type,
                  edit_template, success_url, object_id, **kwargs):
  # pylint: disable-msg=R0913
  """Generic method to handle editing objects with Django forms.

  Args:
    request: the http request
    model_type: the class of object being edited
    model_form_type: the form type to use for editing this object
    edit_template: the template to use for editing the object
    success_url: the URL to redirect the user to when the editing is succesful
    object_id: the ID of the object to edit, or None if creating a new object
    kwargs: additional data to be passed to the edit form

  Returns:
    A HTTP response, either a redirect to the success_url or the edit form.

  """
  editing = False
  type_instance = None
  if object_id:
    editing = True
    type_instance = model_type.get_by_id(int(object_id))
    if type_instance is None:
      return http.HttpResponseNotFound('No object exists with key %r',
                                       object_id)

  form = model_form_type(data=request.POST or None, instance=type_instance)

  kwargs['form'] = form
  kwargs['type_instance'] = type_instance
  kwargs['editing'] = editing

  if not request.POST:
    return respond(request, edit_template, kwargs)

  errors = form.errors
  if not errors:
    try:
      type_instance = form.save(commit=False)
    except ValueError, err:
      errors['__all__'] = unicode(err)
  if errors:
    return respond(request, edit_template, kwargs)

  if 'callback' in kwargs:
    kwargs['callback'](type_instance, kwargs['params'])

  type_instance.put()

  return http.HttpResponseRedirect(success_url)


def set_up_data_store():
  """Function to initialize a new installation.

  Returns:
    The root Page object

  """
  acl = models.AccessControlList(global_read=True)
  acl.put()
  root = models.Page(name='Home', title='Welcome to App Engine Site Creator')
  root.acl = acl
  root.put()
  return root
