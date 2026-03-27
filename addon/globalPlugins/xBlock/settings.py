# settings.py

import wx
import gui
import inputCore
import gui.settingsDialogs

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