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

"""Datastore models."""

from django.core import urlresolvers
from django.core import validators
from django.utils import encoding
from google.appengine.ext import db

import utility
import yaml


class AccessControlList(db.Model):
  # pylint: disable-msg=R0904
  """Model defining access to objects in the system."""
  group_write = db.ListProperty(db.Key)
  user_write = db.ListProperty(db.Key)
  global_write = db.BooleanProperty()
  group_read = db.ListProperty(db.Key)
  user_read = db.ListProperty(db.Key)
  global_read = db.BooleanProperty()

  def clone(self):
    """Returns a duplicate copy of the ACL.

    Returns:
      A cloned version of the ACL to be used when a child page wants to change
      its security.

    """
    new_acl = AccessControlList(group_write=self.group_write,
                                user_write=self.user_write,
                                global_write=self.global_write,
                                group_read=self.group_read,
                                user_read=self.user_read,
                                global_read=self.global_read)
    return new_acl

  def put(self):
    """Saves the ACL and flushes the memcache."""
    super(AccessControlList, self).put()
    utility.clear_memcache()

  def __has_access(self, user, access_type):
    """Determines if user has the specified access type.

    Args:
      user: UserProfile to check
      access_type: Type of access to check, either 'read' or 'write'

    Returns:
      True if the user has the requested access, False otherwise

    """
    if user is not None:
      key = 'acl-has-%s:%s-%s' % (access_type, self.key().id(), user.key().id())
    else:
      key = 'acl-has-%s:%s' % (access_type, self.key().id())
    has_access = utility.memcache_get(key)

    if has_access is not None:
      return has_access

    global_access = self.__getattribute__('global_%s' % access_type)
    user_list = self.__getattribute__('user_%s' % access_type)
    group_list = self.__getattribute__('group_%s' % access_type)
    
    if global_access:
      has_access = True
        
    if user is not None:
      if user.is_superuser or user.key() in user_list:
        has_access = True
      else:
        for group in UserGroup.get(group_list):
          if user.key() in group.users:
            has_access = True
            break

    if has_access is None:
      has_access = False

    utility.memcache_set(key, has_access)
    return has_access

  def user_can_write(self, user):
    """Determines if user has write access.

    Args:
      user: UserProfile to check

    Returns:
      True if the user has write access, False otherwise

    """
    return self.__has_access(user, 'write')

  def user_can_read(self, user):
    """Determines if user has read access.

    Args:
      user: UserProfile to check

    Returns:
      True if the user has read access, False otherwise

    """
    if self.user_can_write(user):
      return True

    return self.__has_access(user, 'read')


class File(db.Model):
  # pylint: disable-msg=R0904
  """Defines common properties and methods for pages and files."""
  name = db.StringProperty(required=True)
  created = db.DateTimeProperty(auto_now_add=True)
  modified = db.DateTimeProperty(auto_now=True)
  parent_page = db.SelfReferenceProperty()
  acl_data = db.ReferenceProperty(AccessControlList)

  def put(self):
    """Overridden method to flush the memcache."""
    if self.acl_data:
      self.acl_data.put()
    super(File, self).put()
    utility.clear_memcache()

  def delete(self):
    """Overridden method to clean up ACLs and to flush the memcache."""
    if self.acl_data:
      self.acl_data.delete()
    super(File, self).delete()
    utility.clear_memcache()

  def __get_acl(self):
    """Returns the ACL for the object by recursion up the path."""
    key = 'acl:%s' % self.key().id()
    acl = utility.memcache_get(key)
    if acl:
      return acl

    if self.acl_data:
      acl = self.acl_data

    if not acl:
      acl = self.parent_page.acl

    utility.memcache_set(key, acl)
    return acl

  def __set_acl(self, data):
    """Sets the underlying acl.

    Args:
      data: The new ACL to use

    """
    self.acl_data = data

  acl = property(__get_acl, __set_acl)

  def inherits_acl(self):
    """Determines if the file is inheriting its ACL from its parent.

    Returns:
      True if the file does not have it's own ACL, and therefore is inheriting,
      otherwise False

    """
    return self.acl_data is None

  def inherits_acl_from(self):
    """Determines which ancestor file the ACL is inherited from.

    Returns:
      The Page object that has the ACL controlling the security for this page

    """
    if self.inherits_acl():
      return self.parent_page.inherits_acl_from()
    else:
      return self

  def user_can_write(self, user):
    """Wrapper method to check if user can write to this file.

    Args:
      user: UserProfile to check

    Returns:
      True if the user has write access otherwise False

    """
    return self.acl.user_can_write(user)

  def user_can_read(self, user):
    """Wrapper method to check if user can read this file.

    Args:
      user: UserProfile to check

    Returns:
      True if the user has read access otherwise False

    """
    return self.acl.user_can_read(user)

  @property
  def path(self):
    """Returns the URL path used to access the page."""
    if self.is_root:
      return ''
    return '%s%s/' % (self.parent_page.path, self.name)

  @property
  def is_root(self):
    """Returns True for the root page, False for all others."""
    return self.parent_page is None


class Page(File):
  # pylint: disable-msg=R0904
  """Defines a page object which may have HTML content and associated files."""

  title = db.StringProperty()
  content = db.TextProperty()

  def delete(self):
    """Overridden to ensure child objects are cleaned up on delete."""
    for page in self.page_children:
      page.delete()
    for file_store in self.filestore_children:
      file_store.delete()
    super(Page, self).delete()

  def get_child(self, name):
    """Returns the child with the given name."""
    return self.page_children.filter('name =', name).get()

  def in_sidebar(self):
    """Determines if the page is referenced in the sidebar."""
    return Sidebar.contains_page(self)

  @staticmethod
  def get_root():
    """Returns the root page."""
    key = 'rootpage'
    root = utility.memcache_get(key)
    if not root:
      root = Page.all().filter('parent_page =', None).get()
      utility.memcache_set(key, root)
    return root

  @property
  def page_children(self):
    """Returns a query for all of the child FileStore objects."""
    return Page.all().filter('parent_page = ', self)

  @property
  def filestore_children(self):
    """Returns a query for all of the child FileStore objects."""
    return FileStore.all().filter('parent_page = ', self)
  
  @property
  def breadcrumbs(self):
    """Returns the HTML representation of the breadcrumbs for the page."""
    key = 'breadcrumbs:%s' % self.key().id()
    breadcrumbs = utility.memcache_get(key)
    
    if breadcrumbs:
      return breadcrumbs
    
    breadcrumbs = []
    if self.parent_page:
      breadcrumbs = self.parent_page.breadcrumbs
      breadcrumbs.append({'path': '/' + self.parent_page.path,
                          'name': self.parent_page.name})
      
    utility.memcache_set(key, breadcrumbs)
    return breadcrumbs 

  def get_attachment(self, name):
    """Retrieves a file with the given name that is attached to the page.

    Args:
      name: name of the file to retrieve

    Returns:
      A FileStore object.

    """
    return self.filestore_children.filter('name =', name).get()

  def attached_files(self):
    """Returns all files attached to the current page.

    Returns:
      A query representing the list of all attached files

    """
    key = 'file-list:%s' % self.key().id()
    file_list = utility.memcache_get(key)
    if not file_list:
      # Convert the iterator to a list for caching
      file_list = list(self.filestore_children.order('name'))
      utility.memcache_set(key, file_list)
    return file_list


class FileStoreData(db.Model):
  """A class that holds the data for a FileStore object."""

  data = db.BlobProperty()
  modified = db.DateTimeProperty(auto_now=True)


class FileStore(File):
  # pylint: disable-msg=R0904
  """A class that represents a single file attached to a page.

  This class contains a property data which abstracts the underlying child
  FileStoreData object.  The data property should be treated as though
  it were a BlobProperty.  This prevents the Blob being read into memory
  until it is actually referenced.

  """

  is_hidden = db.BooleanProperty(default=False)
  url_data = db.LinkProperty()
  blob_data = db.ReferenceProperty(FileStoreData)

  def __get_data(self):
    """Retrieves the data from the child object."""
    return self.blob_data.data

  def __set_data(self, data):
    """Sets the data on the child object, creating one if necessary."""
    if not data:
      if self.blob_data:
        self.blob_data.delete()
        self.blob_data = None
        self.put()
      return

    if not self.blob_data:
      file_store_data = FileStoreData()
      file_store_data.put()
      self.blob_data = file_store_data
      self.put()
    self.blob_data.data = data
    self.blob_data.put()
    self.url = None
    self.put()

  data = property(__get_data, __set_data)

  def __get_url(self):
    """Exposes the url property."""
    return self.url_data

  def __set_deal(self, link):
    """Sets the url property and removes any data associated with the file."""
    if link:
      self.url_data = link
      self.data = None
    else:
      self.url_data = None

  url = property(__get_url, __set_deal)

  def delete(self):
    """Overridden to ensure child objects are cleaned up on delete."""
    if self.blob_data:
      self.blob_data.delete()
    super(FileStore, self).delete()


class UserProfile(db.Model):
  # pylint: disable-msg=R0904
  """A class that represents the access levels of a given user."""

  email = db.EmailProperty(required=True)
  is_superuser = db.BooleanProperty(default=False)

  def __str__(self):
    """Overridden string representation."""
    return self.email

  @staticmethod
  def load(email):
    """Retrieves a given user profile, through memcache if possible.

    Args:
      email: email address of the profile to load

    Returns:
      UserProfile object for the given email address

    """
    key = 'email:' + email
    profile = utility.memcache_get(key)
    if not profile:
      profile = UserProfile.all().filter('email =', email).get()
      utility.memcache_set(key, profile)
    return profile

  def put(self):
    """Saves the profile and flushes the memcache."""
    super(UserProfile, self).put()
    utility.clear_memcache()

  @property
  def groups(self):
    """Returns a list of all of the groups the user is in.

    Returns:
      The list of groups the user is in

    """
    key = 'users_groups:%s' % self.key().id()
    groups = utility.memcache_get(key)
    if not groups:
      groups = list(UserGroup.all().filter('users = ', self.key()))
      utility.memcache_set(key, groups)
    return groups

  @property
  def groups_not_in(self):
    """Returns a list of all of the groups the user is not in.

    Returns:
      The list of groups the user is not in

    """
    all_group_keys = [g.key().id() for g in UserGroup.all_groups()]
    self_group_keys = [g.key().id() for g in self.groups]
    not_in_group_keys = [k for k in all_group_keys if k not in self_group_keys]
    return UserGroup.get_by_id(not_in_group_keys)

  def delete(self):
    """Overridden to ensure memcache is cleared."""
    super(UserProfile, self).delete()
    utility.clear_memcache()

  @staticmethod
  def update(email, is_superuser=False):
    """Creates or updates a user's profile.

    Args:
      email: the email address of the user to add or edit
      is_superuser: boolean value denoting if the user should be an editor

    Returns:
      True if the user is created/edited, False if the email address is invalid

    """
    if not validators.email_re.search(email):
      return False

    user = UserProfile.load(email)
    if user:
      user.is_superuser = is_superuser
    else:
      user = UserProfile(email=email, is_superuser=is_superuser)

    user.put()
    return True


class UserGroup(db.Model):
  # pylint: disable-msg=R0904
  """Model for logically grouping users for access control."""

  name = db.StringProperty(required=True)
  description = db.StringProperty()
  users = db.ListProperty(db.Key)

  def __str__(self):
    """Overridden string representation."""
    return encoding.smart_str(self.name)

  def put(self):
    """Overridden method to ensure name is kept unique."""
    for group in UserGroup.all().filter('name = ', self.name):
      if not self.is_saved() or group.key() != self.key():
        raise db.BadValueError('There is already a group named "%s"'
                               % self.name)
    super(UserGroup, self).put()
    utility.clear_memcache()

  def delete(self):
    """Overridden to ensure memcache is cleared."""
    super(UserGroup, self).delete()
    utility.clear_memcache()

  @staticmethod
  def all_groups():
    """Returns a list of all of the groups in the system.

    Returns:
      A list of all groups

    """
    key = 'all_groups:'
    groups = utility.memcache_get(key)
    if not groups:
      groups = list(UserGroup.all())
      utility.memcache_set(key, groups)
    return groups


class Sidebar(db.Model):
  # pylint: disable-msg=R0904
  """Model for the left-hand navigation."""

  yaml = db.TextProperty(required=True)
  modified = db.DateTimeProperty(auto_now=True)

  def __try_parse(self):
    """Attempts to parse the provided YAML.

    If the YAML is malformed or the expected keys are not present exceptions
    will be thrown.

    """
    for section in yaml.load_all(self.yaml):
      if section['heading']:
        for item in section['pages']:
          if item['id']:
            if item['title']:
              pass

  def put(self):
    """Saves the sidebar and flushes the memcache."""
    self.__try_parse()
    super(Sidebar, self).put()
    utility.clear_memcache()

  @staticmethod
  def load():
    """Retrieves the sidebar from the datastore.

    Returns:
      SideBar object

    """
    return Sidebar.all().get()

  @staticmethod
  def contains_page(page):
    """Determines if the page is referenced in the sidebar.

    Args:
      page: Page to check if it exists in the sidebar

    """
    key = 'page-in-sidebar:%s' % page.key().id()
    in_sidebar = utility.memcache_get(key)
    if in_sidebar is not None:
      return in_sidebar

    sidebar = Sidebar.load()

    if sidebar is not None:
      for section in yaml.load_all(sidebar.yaml):
        for item in section['pages']:
          if item['id'] == page.key().id():
            utility.memcache_set(key, True)
            return True

    utility.memcache_set(key, False)
    return False

  @staticmethod
  def add_page(page):
    """Appends a page to the bottom of the sidebar.

    Args:
      page: Page to append

    """
    sidebar = Sidebar.load()

    if sidebar is None:
      sidebar = Sidebar(yaml="---\nheading: ''\n\n")

    sidebar_documents = list(yaml.load_all(sidebar.yaml))
    if sidebar_documents:
      last_document = sidebar_documents[-1]
      if not last_document.has_key('pages'):
        last_document['pages'] = []
      last_document['pages'].append({'id': page.key().id(),
                                     'title': page.title})

    sidebar.yaml = yaml.safe_dump_all(sidebar_documents)
    sidebar.put()

  @staticmethod
  def render(profile):
    """Retrieves the HTML for the sidebar.

    This method first checks the memcache layer for rendered HTML based on the
    given profile's access level and returns it if found.  If the HTML is not
    found, the sidebar's definition is loaded and each page is checked for
    existence and if the profile's access level has rights to view the page.
    HTML is then rendered and stored in memcache for future accesses

    Args:
      profile: profile of the user accessing the sidebar

    Returns:
      A string containing the HTML of the sidebar for the given profile's
      access level

    """
    if profile is not None:
      key = 'sidebar:%s' % profile.key().id()        
    else:
      key = 'sidebar'
         
    html = utility.memcache_get(key)
    if html:
      return html

    html = []
    sidebar = Sidebar.load()

    if not sidebar:
      return ''

    for section in yaml.load_all(sidebar.yaml):
      section_html = []

      for item in section['pages']:
        # pylint: disable-msg=E1103
        page = Page.get_by_id(int(item['id']))
        if not page or not page.user_can_read(profile):
          continue
        url = urlresolvers.reverse('views.main.get_url', args=[page.path])
        section_html.append('<li><a href="%s">%s</a></li>\n' %
                            (url, item['title']))

      if section_html:
        html.append('<h1>%s</h1>\n' % section['heading'])
        html.append('<ul>\n%s</ul>\n' % ''.join(section_html))

    html = ''.join(html)
    utility.memcache_set(key, html)
    return html
