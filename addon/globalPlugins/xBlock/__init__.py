# __init__.py
# Copyright (C) 2026 Chai Chaimee
# Licensed under GNU General Public License. See COPYING.txt for details.

import globalPluginHandler
import gui
from scriptHandler import script
import addonHandler
import gui.settingsDialogs

from .config import get_config
from .dialog import XBlockDialog
from .settings import XBlockSettingsPanel

addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("xBlock")

	def __init__(self):
		super().__init__()
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(XBlockSettingsPanel)

	def terminate(self):
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
			gui.mainFrame.popupSettingsDialog(XBlockDialog, get_config())
		except AttributeError:
			dlg = XBlockDialog(gui.mainFrame, get_config())
			dlg.ShowModal()
			dlg.Destroy()
		except Exception as e:
			from logHandler import log
			log.error(f"Error opening xBlock dialog: {e}")