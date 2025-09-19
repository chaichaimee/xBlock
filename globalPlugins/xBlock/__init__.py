# __init__.py
# Copyright (C) 2025 chai chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import globalPluginHandler
import globalVars
import os
import api
import wx
import gui
from keyboardHandler import KeyboardInputGesture
from configobj import ConfigObj
import time
import watchdog
from scriptHandler import script
import addonHandler
import inputCore
import gui.settingsDialogs
import core
import winUser

addonHandler.initTranslation()

_xbIniFile = os.path.abspath(os.path.join(globalVars.appArgs.configPath, "xBlock.ini"))
config = ConfigObj(_xbIniFile, list_values=True, encoding="utf-8")

if globalVars.appArgs.secure:
    GlobalPlugin = globalPluginHandler.GlobalPlugin

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("xBlock")

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        self.dialog = None
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(XBlockSettingsPanel)

    def terminate(self):
        if self.dialog is not None:
            self.dialog.Destroy()
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(XBlockSettingsPanel)
        except ValueError:
            pass

    @script(
        description=_("Opens xBlock dialog to manage and paste text blocks"),
        category=_("xBlock"),
        gestures=["kb:windows+f11"],
        allowInSleepMode=True
    )
    def script_openXBlock(self, gesture):
        try:
            gui.mainFrame.popupSettingsDialog(XBlockDialog)
        except AttributeError:
            gui.mainFrame._popupSettingsDialog(XBlockDialog)

class XBlockDialog(wx.Dialog):
    def __init__(self, parent):
        super(XBlockDialog, self).__init__(parent, title=_("xBlock"))
        self.blocks = self.loadBlocks()
        self.selectedBlock = None
        self.editing = False
        self.editingBlockName = None
        self.initUI()

    def initUI(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        # Block list
        listLabel = wx.StaticText(self, label=_("Text blocks:"))
        mainSizer.Add(listLabel, 0, wx.ALL, 5)
        
        # Sort keys to display them alphabetically
        sorted_keys = sorted(list(self.blocks.keys()))
        self.blockList = wx.ListBox(self, choices=sorted_keys, style=wx.LB_SINGLE)
        self.blockList.SetFocus()
        if self.blockList.GetCount() > 0:
            self.blockList.SetSelection(0)
            self.selectedBlock = self.blockList.GetString(0)
        mainSizer.Add(self.blockList, 1, wx.EXPAND | wx.ALL, 5)
        
        # Block name
        nameLabel = wx.StaticText(self, label=_("Block name:"))
        mainSizer.Add(nameLabel, 0, wx.ALL, 5)
        
        self.nameCtrl = wx.TextCtrl(self)
        mainSizer.Add(self.nameCtrl, 0, wx.EXPAND | wx.ALL, 5)
        
        # Block content
        contentLabel = wx.StaticText(self, label=_("Block content:"))
        mainSizer.Add(contentLabel, 0, wx.ALL, 5)
        
        self.contentCtrl = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        mainSizer.Add(self.contentCtrl, 1, wx.EXPAND | wx.ALL, 5)
        
        # Buttons
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.addButton = wx.Button(self, label=_("&Add"))
        buttonSizer.Add(self.addButton, 0, wx.ALL, 5)
        
        self.editButton = wx.Button(self, label=_("&Edit"))
        buttonSizer.Add(self.editButton, 0, wx.ALL, 5)
        
        self.pasteButton = wx.Button(self, label=_("&Paste"))
        buttonSizer.Add(self.pasteButton, 0, wx.ALL, 5)
        
        self.removeButton = wx.Button(self, label=_("&Remove"))
        buttonSizer.Add(self.removeButton, 0, wx.ALL, 5)
        
        self.closeButton = wx.Button(self, id=wx.ID_CLOSE)
        buttonSizer.Add(self.closeButton, 0, wx.ALL, 5)
        
        mainSizer.Add(buttonSizer, 0, wx.ALIGN_CENTER)
        
        self.SetSizer(mainSizer)
        self.SetSize(600, 500)
        self.Centre()
        
        # Set escape ID for ESC key
        self.SetEscapeId(self.closeButton.GetId())
        
        self.Bind(wx.EVT_LISTBOX, self.onBlockSelect, self.blockList)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.onPaste, self.blockList)
        self.Bind(wx.EVT_BUTTON, self.onAdd, self.addButton)
        self.Bind(wx.EVT_BUTTON, self.onEdit, self.editButton)
        self.Bind(wx.EVT_BUTTON, self.onPaste, self.pasteButton)
        self.Bind(wx.EVT_BUTTON, self.onRemove, self.removeButton)
        self.Bind(wx.EVT_BUTTON, self.onClose, self.closeButton)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        
        # Bind Enter key in list to paste action
        self.blockList.Bind(wx.EVT_KEY_DOWN, self.onListKeyDown)
        
        self.updateButtonStates()

    def loadBlocks(self):
        if 'blocks' not in config:
            config['blocks'] = {}
        return config['blocks']

    def saveBlocks(self):
        config.write()

    def updateButtonStates(self):
        hasSelection = self.blockList.GetSelection() != wx.NOT_FOUND
        self.editButton.Enable(hasSelection)
        self.pasteButton.Enable(hasSelection)
        self.removeButton.Enable(hasSelection)
        if hasSelection:
            self.pasteButton.SetDefault()

    def onListKeyDown(self, event):
        keyCode = event.GetKeyCode()
        if keyCode == wx.WXK_RETURN and self.blockList.GetSelection() != wx.NOT_FOUND:
            self.onPaste(event)
        elif keyCode == wx.WXK_RETURN and self.blockList.GetCount() == 0:
            self.onAdd(event)
        else:
            event.Skip()

    def onBlockSelect(self, event):
        self.selectedBlock = self.blockList.GetStringSelection()
        self.updateButtonStates()

    def onAdd(self, event):
        name = self.nameCtrl.GetValue().strip()
        content = self.contentCtrl.GetValue()
        
        if not name:
            wx.MessageBox(_("Please enter a block name"), _("Error"), wx.OK | wx.ICON_ERROR)
            return
            
        if name in self.blocks and not self.editing:
            wx.MessageBox(_("A block with this name already exists"), _("Error"), wx.OK | wx.ICON_ERROR)
            return
        
        old_name = None
        if self.editing:
            old_name = self.editingBlockName
            if old_name and old_name != name:
                del self.blocks[old_name]
        
        # Add new block or update existing - preserve all special characters and whitespace
        self.blocks[name] = content.splitlines()
        self.saveBlocks()
        
        # Update list and sort alphabetically
        sorted_keys = sorted(list(self.blocks.keys()))
        self.blockList.Set(sorted_keys)
        self.blockList.SetStringSelection(name)
        self.selectedBlock = name
        
        # Clear input fields and reset state
        self.nameCtrl.SetValue("")
        self.contentCtrl.SetValue("")
        self.editing = False
        self.editingBlockName = None
        
        self.updateButtonStates()

    def onEdit(self, event):
        if not self.selectedBlock:
            return
            
        # Load selected block into input fields
        content = "\n".join(self.blocks[self.selectedBlock])
        self.nameCtrl.SetValue(self.selectedBlock)
        self.contentCtrl.SetValue(content)
        self.editing = True
        self.editingBlockName = self.selectedBlock

    def onPaste(self, event):
        if not self.selectedBlock or self.selectedBlock not in self.blocks:
            return
        
        self.Hide()
        content = "\r\n".join(self.blocks[self.selectedBlock])
        if len(self.blocks[self.selectedBlock]) >= 2:
            content += "\r\n"
        
        try:
            clipboardBackup = api.getClipData()
        except OSError:
            clipboardBackup = None
        
        try:
            api.copyToClip(content)
            time.sleep(0.1 if clipboardBackup is None else 0.01)
            api.processPendingEvents(False)
        except Exception as e:
            from logHandler import log
            log.error(f"Error copying to clipboard: {e}")
            wx.MessageBox(_("Failed to copy to clipboard"), _("Error"), wx.OK | wx.ICON_ERROR)
            self.Destroy()
            return
        
        focus = api.getFocusObject()
        # Use alternative pasting methods for different window types
        try:
            if hasattr(focus, 'windowClassName') and focus.windowClassName == "ConsoleWindowClass":
                # Windows console window - Control+V doesn't work here
                WM_COMMAND = 0x0111
                watchdog.cancellableSendMessage(focus.windowHandle, WM_COMMAND, 0xfff1, 0)
            elif hasattr(focus, 'windowClassName') and "Rich" in focus.windowClassName and "Text" in focus.windowClassName:
                # Rich Text controls - use WM_PASTE message
                WM_PASTE = 0x0302
                watchdog.cancellableSendMessage(focus.windowHandle, WM_PASTE, 0, 0)
            else:
                # For other windows, try multiple methods
                try:
                    # First try standard Ctrl+V
                    KeyboardInputGesture.fromName("control+v").send()
                except Exception:
                    # If that fails, try alternative methods
                    try:
                        # Try Shift+Insert as alternative
                        KeyboardInputGesture.fromName("shift+insert").send()
                    except Exception:
                        # Last resort: use WM_PASTE if we have a window handle
                        if hasattr(focus, 'windowHandle') and focus.windowHandle:
                            WM_PASTE = 0x0302
                            watchdog.cancellableSendMessage(focus.windowHandle, WM_PASTE, 0, 0)
                        else:
                            # If all else fails, focus might be in a non-standard control
                            # Try to set focus to the object and retry standard paste
                            try:
                                focus.setFocus()
                                time.sleep(0.05)
                                KeyboardInputGesture.fromName("control+v").send()
                            except Exception:
                                raise
        except Exception as e:
            from logHandler import log
            log.error(f"Error pasting text: {e}")
            wx.MessageBox(_("Failed to paste text. Please try manual paste (Ctrl+V)."), _("Error"), wx.OK | wx.ICON_ERROR)
        
        if clipboardBackup is not None:
            core.callLater(300, lambda: api.copyToClip(clipboardBackup))
        
        self.Destroy()

    def onRemove(self, event):
        if not self.selectedBlock:
            return
            
        confirm = wx.MessageBox(
            _("Are you sure you want to delete the block '{name}'?").format(name=self.selectedBlock),
            _("Confirm deletion"),
            wx.YES_NO | wx.ICON_QUESTION
        )
        
        if confirm == wx.YES:
            del self.blocks[self.selectedBlock]
            self.saveBlocks()
            
            # Update UI and sort alphabetically
            sorted_keys = sorted(list(self.blocks.keys()))
            self.blockList.Set(sorted_keys)
            if self.blockList.GetCount() > 0:
                self.blockList.SetSelection(0)
                self.selectedBlock = self.blockList.GetString(0)
            else:
                self.selectedBlock = None
                
            self.updateButtonStates()

    def onClose(self, event):
        self.Destroy()

class XBlockSettingsPanel(gui.settingsDialogs.SettingsPanel):
    title = _("xBlock")

    def makeSettings(self, settingsSizer):
        sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.gestureEditor = sHelper.addLabeledControl(
            _("&Shortcut to open xBlock:"),
            inputCore.GestureInput,
            gesture="kb:windows+alt+x"
        )

    def onSave(self):
        gesture = self.gestureEditor.getValue()
        try:
            inputCore.manager.userGestureMap.add(
                gesture,
                "globalPlugins.xBlock",
                "GlobalPlugin",
                "openXBlock"
            )
            inputCore.manager.userGestureMap.save()
        except Exception as e:
            from logHandler import log
            log.error(f"Error saving gesture: {e}")
