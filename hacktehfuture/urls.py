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

"""Defines the url patterns for the application."""

# pylint: disable-msg=C0103,C0301

from django.conf.urls import defaults

urlpatterns = defaults.patterns(
    'views',
    (r'^admin/$', 'admin.index'),
    (r'^admin/recent/$', 'admin.recently_modified'),
    (r'^admin/new/(\d*)$', 'admin.new_page'),
    (r'^admin/edit/sidebar/$', 'admin.edit_sidebar'),
    (r'^admin/edit/add_to_sidebar/(\d+)$', 'admin.add_to_sidebar'),
    (r'^admin/edit/user/([^\s/]*)$', 'admin.edit_user'),
    (r'^admin/users/$', 'admin.filter_users'),
    (r'^admin/users/listgroups/$', 'admin.list_groups'),
    (r'^admin/users/newgroup/$', 'admin.new_group'),
    (r'^admin/users/addtogroup/(\d+)/([^\s/]*)$', 'admin.add_to_group'),
    (r'^admin/users/removefromgroup/(\d+)/([^\s/]*)$', 'admin.remove_from_group'),
    (r'^admin/users/editgroup/([\w\-]+)$', 'admin.edit_group'),
    (r'^admin/users/deletegroup/([\w\-]+)$', 'admin.delete_group'),
    (r'^admin/users/bygroup/([\w\-]*)$', 'admin.view_group'),
    (r'^admin/editacl$', 'admin.edit_acl'),
    (r'^admin/bulkeditusers/$', 'admin.bulk_edit_users'),
    (r'^admin/exportusers/$', 'admin.export_users'),
    (r'^admin/edit/(\d+)/$', 'admin.edit_page'),
    (r'^admin/deletepage/([^\s]+)/$', 'admin.delete_page'),
    (r'^admin/download/([\w\-]+).html$', 'admin.download_page_html'),
    (r'^admin/addfile/$', 'admin.upload_file'),
    (r'^admin/deletefile/([\w\-]+)/([^\s/]+)$', 'admin.delete_file'),
    (r'^admin/help/$', 'admin.get_help'),
    (r'^admin/memcache_info/$', 'admin.display_memcache_info'),
    (r'^admin/memcache_info/flush/$', 'admin.flush_memcache_info'),
    (r'^_treedata/$', 'main.get_tree_data'),
    (r'^sitemap/$', 'main.page_list'),
    (r'^(.*)$', 'main.get_url'),
)

handler404 = 'utility.page_not_found'
handler500 = defaults.handler500
