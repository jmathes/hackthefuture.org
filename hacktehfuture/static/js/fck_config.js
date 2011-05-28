/*
 * Copyright 2008 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

var pluginPath = '/static/js/plugins/';

FCKConfig.SkinPath = FCKConfig.BasePath + 'skins/silver/';
FCKConfig.Plugins.Add('gadget', 'en', pluginPath);

FCKConfig.ToolbarSets['AESC_Toolbar'] = [
  ['FitWindow','Source','-'],
  ['Undo','Redo','-','Find','Replace'],
  ['Bold','Italic','Underline','StrikeThrough'],
  ['OrderedList','UnorderedList','-','Outdent','Indent'],
  ['JustifyLeft','JustifyCenter','JustifyRight','JustifyFull'],
  ['Link','Unlink'],
  ['Gadget', 'Image','Flash','Table','SpecialChar'],
  '/',
  ['Style','FontFormat','FontName','FontSize'],
  ['TextColor','BGColor'] // No comma for the last row.
];

FCKConfig.ImageBrowser = false;
FCKConfig.ImageUpload = false;
FCKConfig.LinkBrowser = false;