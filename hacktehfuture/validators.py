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

"""Custom validators."""

import re
from django import forms

PAGE_NAME_RE = re.compile(r'^([\w\-]+)$')


def is_valid_page_name(field_data):
  """Validator for page name input.

  Determines if the name provided by the user is a valid name to use as a
  URL in the system

  Args:
    field_data: Data input by the user on the form

  Raises:
    ValidationError: The input data is not acceptable as a page name

  """
  if not PAGE_NAME_RE.search(field_data):
    raise forms.ValidationError('A valid page name can only contain '
                                'alphanumeric characters, underscores and '
                                'hyphens')
