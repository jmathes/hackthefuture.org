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

// Register the related command.
FCKCommands.RegisterCommand(
    'Gadget',
    new FCKDialogCommand(
        'Gadget',
        FCKLang.GadgetDlgTitle,
        FCKPlugins.Items['gadget'].Path + 'gadget.html',
        340, 240));

// Create the "Gadget" toolbar button.
var oGadgetItem = new FCKToolbarButton('Gadget', FCKLang.GadgetBtn);
oGadgetItem.IconPath = FCKPlugins.Items['gadget'].Path + 'gadget.png' ;
FCKToolbarItems.RegisterItem('Gadget', oGadgetItem);
