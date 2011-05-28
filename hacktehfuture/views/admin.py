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

"""Administrative views for page editing and user management."""

import csv
import functools
import logging
import StringIO

from django import http
from django.core import urlresolvers
from django.core import validators
from django.core import exceptions
from django.utils import translation
import forms
from google.appengine.api import memcache
from google.appengine.ext import db
import models
import utility
import yaml


def admin_required(func):
  """Ensure that the logged in user is an administrator."""

  @functools.wraps(func)
  def __wrapper(request, *args, **kwds):
    """Makes it possible for admin_required to be used as a decorator."""
    if request.user_is_admin:
      return func(request, *args, **kwds)  # pylint: disable-msg=W0142
    else:
      return utility.forbidden(
          request,
          error_message='You must be an administrator to view this page.')

  return __wrapper


def super_user_required(func):
  """Ensure that the logged in user has editing privileges."""

  @functools.wraps(func)
  def __wrapper(request, *args, **kwds):
    """Makes it possible for super_user_required to be used as a decorator."""
    if request.profile.is_superuser:
      return func(request, *args, **kwds)  # pylint: disable-msg=W0142
    else:
      return utility.forbidden(
          request,
          error_message='You must be a superuser to view this page.')

  return __wrapper


@super_user_required
def index(request):
  """Show the root administrative page."""
  return utility.respond(request, 'admin/index')


@super_user_required
def recently_modified(request):
  """Show the 10 most recently modified pages."""
  pages = models.Page.all().order('modified').fetch(10)
  return utility.respond(request, 'admin/recently_modified', {'pages': pages})


@super_user_required
def get_help(request):
  """Return a help page for the site maintainer."""
  return utility.respond(request, 'admin/help')


def edit_acl(request):
  """Edits the contents of an ACL."""

  def grant_access(acl, list_to_edit):
    """Grants access to a page based on data in the POST.

    Args:
      acl: AccessControlList to be manipulated
      list_to_edit: string representing the list on the ACL to add users or
                    groups to

    """
    if request.POST[list_to_edit]:
      datastore_object = None
      if request.POST[list_to_edit].startswith('user'):
        datastore_object = models.UserProfile.load(request.POST[list_to_edit])
      else:
        datastore_object = models.UserGroup.get_by_id(
            int(request.POST[list_to_edit]))
      if datastore_object.key() not in acl.__getattribute__(list_to_edit):
        acl.__getattribute__(list_to_edit).append(datastore_object.key())

  def remove_access(acl, list_to_edit):
    """Removes access to a page based on data in the POST.

    Args:
      acl: AccessControlList to be manipulated
      list_to_edit: string representing the list on the ACL to remove users or
                    groups from

    """
    post_key = '%s_remove_' % list_to_edit
    removal_keys = [k for k in request.POST.keys() if k.startswith(post_key)]
    for key in removal_keys:
      model_type = models.UserGroup
      if list_to_edit.startswith('user'):
        model_type = models.UserProfile
      key_id = int(key.replace(post_key, ''))
      datastore_object = model_type.get_by_id(key_id)
      acl.__getattribute__(list_to_edit).remove(datastore_object.key())

  page_id = request.POST['page_id']
  page = models.Page.get_by_id(int(page_id))

  if not page:
    return utility.page_not_found(request)
  if not page.user_can_write(request.profile):
    return utility.forbidden(request)

  acl = page.acl

  if page.inherits_acl():
    acl = acl.clone()
    acl.put()
    page.acl = acl
    page.put()

  acl.global_write = 'global_write' in request.POST
  acl.global_read = 'global_read' in request.POST

  for object_list in ['group_write', 'group_read', 'user_write', 'user_read']:
    grant_access(acl, object_list)
    remove_access(acl, object_list)

  acl.put()

  return utility.edit_updated_page(page_id, tab_name='security',
                                 message_id='msgChangesSaved')


def edit_page(request, page_id, parent_id=None):
  """Generates and processes the form to create or edit a specified page.

  Args:
    request: The request object
    page_id: ID of the page.
    parent_id: ID of the parent page

  Returns:
    A Django HttpResponse object.

  """
  page = None
  files = None

  if page_id:
    page = models.Page.get_by_id(int(page_id))
    if not page:
      return utility.page_not_found(
          request, 'No page exists with id %r.' % page_id)
    if not page.user_can_write(request.profile):
      return utility.forbidden(request)
    files = list(
        models.FileStore.all().filter('parent_page =', page).order('name'))
    for item in files:
      item.icon = '/static/images/fileicons/%s.png' % item.name.split('.')[-1]

  acl_data = None

  if page:
    all_group_keys = [
        g.key() for g in models.UserGroup.all().order('name')]
    groups_without_write_keys = [
        k for k in all_group_keys if k not in page.acl.group_write]
    groups_without_read_keys = [
        k for k in all_group_keys if k not in page.acl.group_read]
    acl_data = {
        'groups_without_write': models.UserGroup.get(groups_without_write_keys),
        'groups_without_read': models.UserGroup.get(groups_without_read_keys),
        'group_write': models.UserGroup.get(page.acl.group_write),
        'group_read': models.UserGroup.get(page.acl.group_read),
        'user_write': models.UserProfile.get(page.acl.user_write),
        'user_read': models.UserProfile.get(page.acl.user_read),
        'inherits_acl': page.inherits_acl(),
    }

  if not request.POST:
    form = forms.PageEditForm(data=None, instance=page)
    return utility.respond(request, 'admin/edit_page',
                           {'form': form, 'page': page, 'files': files,
                            'acl_data': acl_data, 'parent_id': parent_id})

  form = forms.PageEditForm(data=request.POST, instance=page)

  if not form.errors:
    try:
      page = form.save(commit=False)
    except ValueError, err:
      form.errors['__all__'] = unicode(err)
  if form.errors:
    return utility.respond(request, 'admin/edit_page',
                           {'form': form, 'page': page, 'files': files})

  page.content = request.POST['editorHtml']
  if parent_id and not page.parent_page:
    page.parent_page = models.Page.get_by_id(int(parent_id))
  page.put()

  return utility.edit_updated_page(page.key().id(),
                                   message_id='msgChangesSaved')


def new_page(request, parent_id):
  """Create a new page.

  Args:
    request: The request object
    parent_id: Page that will be the parent of the new page

  Returns:
    A Django HttpResponse object.

  """
  if parent_id:
    parent_page = models.Page.get_by_id(int(parent_id))
  else:
    parent_page = models.Page.get_root()
    if parent_page:
      # there is a root, lets force everything to be a child of the root
      # and set the parent_id
      parent_id = parent_page.key().id()
    else:
      # TODO(gpennington): Figure out a more intuitive method for site
      # initialization
      parent_page = utility.set_up_data_store()
      return utility.edit_updated_page(parent_page.key().id())

  if not parent_page.user_can_write(request.profile):
    return utility.forbidden(request)
  return edit_page(request, None, parent_id=parent_id)


def upload_file(request):
  """Reads a file from POST data and stores it in the db.

  Args:
    request: The request object

  Returns:
    A http redirect to the edit form for the parent page

  """
  if not request.POST or not 'page_id' in request.POST:
    return utility.page_not_found(request)

  page_id = request.POST['page_id']
  page = models.Page.get_by_id(int(page_id))
  
  if not page:
    logging.warning('admin.upload_file was passed an invalid page id %r',
                    page_id)
    return utility.page_not_found(request)

  if not page.user_can_write(request.profile):
    return utility.forbidden(request)

  file_data = None
  file_name = None
  url = None
  if request.FILES and 'attachment' in request.FILES:
    file_name = request.FILES['attachment'].name
    file_data = request.FILES['attachment'].read()
  elif 'url' in request.POST:
    url = request.POST['url']
    file_name = url.split('/')[-1]
  else:
    return utility.page_not_found(request)

  if not url and not file_name:
    url = 'invalid URL'

  if url:
    validate = validators.URLValidator()
    try:
      validate(url)
    except exceptions.ValidationError, excption:
      return utility.page_not_found(request, excption.messages[0])

  file_record = page.get_attachment(file_name)

  if not file_record:
    file_record = models.FileStore(name=file_name, parent_page=page)

  if file_data:
    file_record.data = db.Blob(file_data)
  elif url:
    file_record.url = db.Link(url)

  # Determine whether to list the file when the page is viewed
  file_record.is_hidden = 'hidden' in request.POST

  file_record.put()
  utility.clear_memcache()

  return utility.edit_updated_page(page_id, tab_name='files')


def delete_file(request, page_id, file_id):
  """Removes a specified file from the database.

  Args:
    request: The request object
    page_id: ID of the page the file is attached to.
    file_id: Id of the file.

  Returns:
    A Django HttpResponse object.

  """
  record = models.FileStore.get_by_id(int(file_id))
  if record:
    if not record.user_can_write(request.profile):
      return utility.forbidden(request)

    record.delete()
    return utility.edit_updated_page(page_id, tab_name='files')
  else:
    return utility.page_not_found(request)


def delete_page(request, page_id):
  """Removes a page from the database.

  The page with name page_name is completely removed from the db, and all files
  attached to that page are removed.

  Args:
    request: The request object
    page_id: Key id of the page to delete

  Returns:
    A http redirect to the admin index page.

  """
  page = models.Page.get_by_id(int(page_id))

  if not page:
    return utility.page_not_found(request)

  if not page.user_can_write(request.profile):
    return utility.forbidden(request)

  page.delete()

  url = urlresolvers.reverse('views.admin.index')
  return http.HttpResponseRedirect(url)


@super_user_required
def download_page_html(request, page_id):
  """Gives users access to the current html content of a page.

  Args:
    request: The request object
    page_id: ID of the page being edited

  Returns:
    A Django HttpResponse object containing the page's html content.

  """
  page = models.Page.get_by_id(int(page_id))
  if not page:
    return utility.page_not_found(request)
  response = http.HttpResponse(content=page.content, mimetype='text/html')
  response['Content-Disposition'] = 'attachment; filename=%s.html' % page.name
  return response


@super_user_required
def filter_users(request):
  """Lists all the UserGroups in the DB to filter the user list.

  Args:
    request: The request object

  Returns:
    A Django HttpResponse object.

  """
  groups = models.UserGroup.all().order('name')
  return utility.respond(request, 'admin/filter_users', {'groups': groups})


@super_user_required
def list_groups(request):
  """Lists all the UserGroups in the DB for editing.

  Args:
    request: The request object

  Returns:
    A Django HttpResponse object.

  """
  groups = models.UserGroup.all().order('name')
  return utility.respond(request, 'admin/list_groups', {'groups': groups})


@super_user_required
def view_group(request, group_id):
  """Lists all the UserProfiles in a group.

  Args:
    request: The request object
    group_id: Id of the group to display

  Returns:
    A Django HttpResponse object.

  """
  users = models.UserProfile.all().order('email')
  if group_id:
    group = models.UserGroup.get_by_id(int(group_id))
    if group.users:
      users = models.UserProfile.get(group.users)
    else:
      users = []
  return utility.respond(request, 'admin/view_group', {'users': users})


@super_user_required
def add_to_group(_request, group_id, email):
  """Adds a user to a group.

  Args:
    _request: The request object (ignored)
    group_id: id of the group to add the user to
    email: email address of the user to add

  Returns:
    A HttpResponse object.

  """
  group = models.UserGroup.get_by_id(int(group_id))
  user_key = models.UserProfile.load(email).key()
  if group.users is None:
    group.users = []
    logging.warning('Group "%s" had a None users list', group.name)
  group.users.append(user_key)
  group.put()

  url = urlresolvers.reverse('views.admin.edit_user', args=[email])
  return http.HttpResponseRedirect(url)


@super_user_required
def remove_from_group(_request, group_id, email):
  """Removes a user from a group.

  Args:
    _request: The request object (ignored)
    group_id: id of the group to remove the user from
    email: email address of the user to remove

  Returns:
    A HttpResponse object.

  """
  group = models.UserGroup.get_by_id(int(group_id))
  user_key = models.UserProfile.load(email).key()
  if group.users is None:
    group.users = []
    logging.warning('Group "%s" had a None users list' % group.name)
  group.users.remove(user_key)
  group.put()

  url = urlresolvers.reverse('views.admin.edit_user', args=[email])
  return http.HttpResponseRedirect(url)


@super_user_required
def new_group(request):
  """Creates a new group.

  Args:
    request: The request object

  Returns:
    A HttpResponse object.

  """
  return edit_group(request, None)


@super_user_required
def edit_group(request, group_id):
  """Edits an existing group or creates a new one if no ID is passed.

  Args:
    request: The request object
    group_id: The ID of the group to edit, or None if this is a new group

  Returns:
    A Django HttpResponse object.

  """
  group = None
  if group_id:
    group = models.UserGroup.get_by_id(int(group_id))
  return utility.edit_instance(request, models.UserGroup, forms.GroupEditForm,
                               'admin/edit_group',
                               urlresolvers.reverse('views.admin.list_groups'),
                               group_id, group=group)


@super_user_required
def delete_group(_request, group_id):
  """Deletes a given group.

  Args:
    _request: The request object (ignored)
    group_id: Id of the group to delete

  Returns:
    A Django HttpResponse object.

  """
  group = models.UserGroup.get_by_id(int(group_id))
  group.delete()

  url = urlresolvers.reverse('views.admin.list_groups')
  return http.HttpResponseRedirect(url)


@super_user_required
def edit_user(request, email):
  """Renders and processes a form to edit a UserProfile.

  Args:
    request: The request object
    email: The user's email

  Returns:
    A Django HttpResponse object.

  """
  if not email:
    if request.POST and request.POST['email']:
      url = urlresolvers.reverse('views.admin.edit_user',
                                 args=[request.POST['email']])
      return http.HttpResponseRedirect(url)
    else:
      title = translation.ugettext('Edit user')
      return utility.respond(request, 'admin/edit_user', {'title': title})

  profile = models.UserProfile.load(email)
  if not profile:
    return utility.page_not_found(request)
  title = translation.ugettext('Edit user: %(email)s') % {'email': email}

  return utility.edit_instance(request, models.UserProfile, forms.UserEditForm,
                               'admin/edit_user',
                               urlresolvers.reverse('views.admin.index'),
                               profile.key().id(), title=title, profile=profile)


@super_user_required
def bulk_edit_users(request):
  """Renders and processes a form to edit UserProfiles with a csv format.

  Args:
    request: The request object

  Returns:
    A Django HttpResponse object.

  """
  if not request.POST:
    title = translation.ugettext('Bulk user upload form')
    return utility.respond(request, 'admin/bulk_edit_users',
                           {'title': title})

  data = request.POST['users_text']
  if data and data[-1] != '\n':
    data += '\n'

  if request.FILES and 'users_file' in request.FILES:
    data += request.FILES['users_file']['content']

  if 'complete' in request.POST:
    for profile in models.UserProfile.all():
      db.delete(profile)

  csv_buffer = StringIO.StringIO(data)
  for email, is_superuser in csv.reader(csv_buffer, skipinitialspace=True):
    if not models.UserProfile.update(email, is_superuser == '1'):
      logging.warning('Could not update user %r' % email)

  url = urlresolvers.reverse('views.admin.index')
  return http.HttpResponseRedirect(url)


@super_user_required
def export_users(_request):
  """Export a csv file listing all UserProfiles in the database.

  Args:
    _request: The request object (ignored)

  Returns:
    The csv file in a HttpResponse object.

  """
  query = models.UserProfile.all().order('email')
  rows = []
  for user in query:
    is_superuser = 0
    if user.is_superuser:
      is_superuser = 1
    rows.append('%s,%s\n' % (user.email, is_superuser))

  response = http.HttpResponse(''.join(rows), mimetype='text/csv')
  response['Content-Disposition'] = 'attachment; filename=users.csv'
  return response


@super_user_required
def add_to_sidebar(_request, page_id):
  """Adds a page to the bottom of the sidebar.

  Args:
    request: The request object (ignored)
    page_id: Id of the page to add to the sidebar

  Returns:
    A Django HttpResponse object.

  """
  page = models.Page.get_by_id(int(page_id))
  models.Sidebar.add_page(page)
  return http.HttpResponseRedirect(
      urlresolvers.reverse('views.admin.edit_sidebar'))


@super_user_required
def edit_sidebar(request):
  """Renders and processes a form to edit the YAML definition of the sidebar.

  Args:
    request: The request object

  Returns:
    A Django HttpResponse object.

  """
  sidebar = models.Sidebar.load()

  if request.POST and 'yaml' in request.POST:
    yaml_data = request.POST['yaml']
    if not sidebar:
      sidebar = models.Sidebar(yaml=yaml_data)
    else:
      sidebar.yaml = yaml_data

    error_message = None
    try:
      sidebar.put()
    except yaml.YAMLError:
      error_message = 'Invalid YAML'
    except KeyError, error:
      error_message = 'Invalid YAML, missing key %s' % error

    if error_message:
      return utility.respond(request, 'admin/edit_sidebar',
                             {'yaml': yaml_data,
                              'error_message': error_message})

    return http.HttpResponseRedirect(urlresolvers.reverse('views.admin.index'))

  else:
    yaml_data = ''
    if sidebar:
      yaml_data = sidebar.yaml
    return utility.respond(request, 'admin/edit_sidebar', {'yaml': yaml_data})


@admin_required
def flush_memcache_info(_request):
  """Flushes the memcache.

  Args:
    _request: The request object (ignored)

  Returns:
    A Django HttpResponse object.

  """
  utility.clear_memcache()
  return http.HttpResponseRedirect(
      urlresolvers.reverse('views.admin.display_memcache_info'))


@admin_required
def display_memcache_info(request):
  """Displays all of the information about the applications memcache.

  Args:
    request: The request object

  Returns:
    A Django HttpResponse object.

  """
  # pylint: disable-msg=E1101
  return utility.respond(request, 'admin/memcache_info',
                         {'memcache_info': memcache.get_stats()})
