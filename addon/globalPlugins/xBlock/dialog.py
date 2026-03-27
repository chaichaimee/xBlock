# dialog.py

import wx
import api
import core
import ui
import watchdog
from keyboardHandler import KeyboardInputGesture
from .config import save_config
from logHandler import log

class XBlockDialog(wx.Dialog):
	def __init__(self, parent, config):
		super().__init__(parent, title=_("xBlock"))
		self.config = config
		self.currentCategory = None
		self.editing = False
		self.editingBlockName = None
		self.editingCategory = None
		self._init_ui()
		self._select_category("All")
		self._update_ui_state()
		wx.CallAfter(self._set_focus)

	def _set_focus(self):
		if self.blockList and self.blockList.IsShown():
			self.blockList.SetFocus()

	def _init_ui(self):
		main_sizer = wx.BoxSizer(wx.HORIZONTAL)

		# Left panel: category list
		left_panel = wx.Panel(self)
		left_sizer = wx.BoxSizer(wx.VERTICAL)

		cat_label = wx.StaticText(left_panel, label=_("Categories:"))
		left_sizer.Add(cat_label, 0, wx.ALL, 5)

		self.categoryList = wx.ListBox(left_panel, style=wx.LB_SINGLE)
		self.categoryList.SetMinSize((150, -1))
		left_sizer.Add(self.categoryList, 1, wx.EXPAND | wx.ALL, 5)

		left_panel.SetSizer(left_sizer)

		# Right panel: blocks and controls
		right_panel = wx.Panel(self)
		right_sizer = wx.BoxSizer(wx.VERTICAL)

		block_label = wx.StaticText(right_panel, label=_("Text blocks:"))
		right_sizer.Add(block_label, 0, wx.ALL, 5)

		self.blockList = wx.ListCtrl(right_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		self.blockList.InsertColumn(0, _("Block Name"), width=400)
		right_sizer.Add(self.blockList, 1, wx.EXPAND | wx.ALL, 5)

		name_label = wx.StaticText(right_panel, label=_("Block name:"))
		right_sizer.Add(name_label, 0, wx.ALL, 5)
		self.nameCtrl = wx.TextCtrl(right_panel)
		right_sizer.Add(self.nameCtrl, 0, wx.EXPAND | wx.ALL, 5)

		content_label = wx.StaticText(right_panel, label=_("Block content:"))
		right_sizer.Add(content_label, 0, wx.ALL, 5)
		self.contentCtrl = wx.TextCtrl(right_panel, style=wx.TE_MULTILINE)
		right_sizer.Add(self.contentCtrl, 1, wx.EXPAND | wx.ALL, 5)

		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.addBtn = wx.Button(right_panel, label=_("&Add"))
		self.editBtn = wx.Button(right_panel, label=_("&Edit"))
		self.pasteBtn = wx.Button(right_panel, label=_("&Paste"))
		self.removeBtn = wx.Button(right_panel, label=_("&Delete"))
		self.moveBtn = wx.Button(right_panel, label=_("Move to Category"))
		self.newCatBtn = wx.Button(right_panel, label=_("New &Category"))
		self.cancelBtn = wx.Button(right_panel, label=_("&Cancel"))
		self.cancelBtn.Hide()
		self.closeBtn = wx.Button(right_panel, id=wx.ID_CLOSE)

		btn_sizer.Add(self.addBtn, 0, wx.ALL, 2)
		btn_sizer.Add(self.editBtn, 0, wx.ALL, 2)
		btn_sizer.Add(self.pasteBtn, 0, wx.ALL, 2)
		btn_sizer.Add(self.removeBtn, 0, wx.ALL, 2)
		btn_sizer.Add(self.moveBtn, 0, wx.ALL, 2)
		btn_sizer.Add(self.newCatBtn, 0, wx.ALL, 2)
		btn_sizer.Add(self.cancelBtn, 0, wx.ALL, 2)
		btn_sizer.Add(self.closeBtn, 0, wx.ALL, 2)

		right_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER)

		right_panel.SetSizer(right_sizer)

		main_sizer.Add(left_panel, 0, wx.EXPAND | wx.ALL, 5)
		main_sizer.Add(right_panel, 1, wx.EXPAND | wx.ALL, 5)
		self.SetSizer(main_sizer)
		self.SetSize(800, 600)
		self.Centre()
		self.SetEscapeId(self.closeBtn.GetId())

		# Bind events
		self.Bind(wx.EVT_LISTBOX, self._on_category_select, self.categoryList)
		self.categoryList.Bind(wx.EVT_KEY_DOWN, self._on_category_key_down)
		self.categoryList.Bind(wx.EVT_CONTEXT_MENU, self._on_category_context_menu)

		self.blockList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_paste)
		self.Bind(wx.EVT_BUTTON, self._on_paste, self.pasteBtn)
		self.Bind(wx.EVT_BUTTON, self._on_remove_block, self.removeBtn)
		self.Bind(wx.EVT_BUTTON, self._on_move_block, self.moveBtn)
		self.Bind(wx.EVT_BUTTON, self._on_add_block, self.addBtn)
		self.Bind(wx.EVT_BUTTON, self._on_edit_block, self.editBtn)
		self.Bind(wx.EVT_BUTTON, self._on_new_category, self.newCatBtn)
		self.Bind(wx.EVT_BUTTON, self._on_cancel_edit, self.cancelBtn)
		self.Bind(wx.EVT_BUTTON, self._on_close, self.closeBtn)
		self.Bind(wx.EVT_CLOSE, self._on_close)

		self.blockList.Bind(wx.EVT_KEY_DOWN, self._on_block_key_down)
		self.blockList.Bind(wx.EVT_CONTEXT_MENU, self._on_block_context_menu)

		# Category context menu
		self.catContextMenu = wx.Menu()
		self.catNewItem = self.catContextMenu.Append(wx.ID_NEW, _("&New Category"))
		self.catEditItem = self.catContextMenu.Append(wx.ID_EDIT, _("&Edit Category"))
		self.catRemoveItem = self.catContextMenu.Append(wx.ID_DELETE, _("&Remove Category"))
		self.Bind(wx.EVT_MENU, self._on_new_category, self.catNewItem)
		self.Bind(wx.EVT_MENU, self._on_edit_category, self.catEditItem)
		self.Bind(wx.EVT_MENU, self._on_remove_category, self.catRemoveItem)

		# Block context menu
		self.blockContextMenu = wx.Menu()
		self.blockSaveItem = self.blockContextMenu.Append(wx.ID_SAVE, _("&Save"))
		self.blockPasteItem = self.blockContextMenu.Append(wx.ID_PASTE, _("&Paste"))
		self.blockEditItem = self.blockContextMenu.Append(wx.ID_EDIT, _("&Edit"))
		self.blockPinItem = self.blockContextMenu.Append(wx.ID_ANY, _("&Pin/Unpin"))
		self.blockMoveUpItem = self.blockContextMenu.Append(wx.ID_ANY, _("Move &Up"))
		self.blockMoveDownItem = self.blockContextMenu.Append(wx.ID_ANY, _("Move &Down"))
		self.blockDeleteItem = self.blockContextMenu.Append(wx.ID_DELETE, _("&Delete"))
		self.Bind(wx.EVT_MENU, self._on_add_block, self.blockSaveItem)
		self.Bind(wx.EVT_MENU, self._on_paste, self.blockPasteItem)
		self.Bind(wx.EVT_MENU, self._on_edit_block, self.blockEditItem)
		self.Bind(wx.EVT_MENU, self._on_toggle_pin, self.blockPinItem)
		self.Bind(wx.EVT_MENU, self._on_move_up, self.blockMoveUpItem)
		self.Bind(wx.EVT_MENU, self._on_move_down, self.blockMoveDownItem)
		self.Bind(wx.EVT_MENU, self._on_remove_block, self.blockDeleteItem)

	def _refresh_category_list(self):
		cats = self.config["Categories"].keys()
		sorted_cats = []
		if "All" in cats:
			sorted_cats.append("All")
		others = sorted([c for c in cats if c != "All"], key=str.lower)
		sorted_cats.extend(others)
		self.categoryList.Set(sorted_cats)
		if self.currentCategory in sorted_cats:
			self.categoryList.SetStringSelection(self.currentCategory)

	def _select_category(self, cat_name):
		if cat_name not in self.config["Categories"]:
			return
		self.currentCategory = cat_name
		self._refresh_category_list()
		self._refresh_and_save(renormalize=True)
		self._clear_inputs()
		self._update_ui_state()

	def _refresh_block_list(self):
		if not self.currentCategory:
			return
		blocks_dict = self.config["Categories"][self.currentCategory]["blocks"]
		for data in blocks_dict.values():
			pinned = data.get("pinned", False)
			if isinstance(pinned, str):
				pinned = pinned.lower() == "true"
			data["pinned"] = pinned
			order = data.get("order", 0)
			try:
				order = int(order)
			except (ValueError, TypeError):
				order = 0
			data["order"] = order

		sorted_items = sorted(blocks_dict.items(),
							  key=lambda x: (not x[1]["pinned"], x[1]["order"]))
		self.blockList.DeleteAllItems()
		for name, _ in sorted_items:
			self.blockList.InsertItem(self.blockList.GetItemCount(), name)
		if sorted_items:
			self.blockList.Select(0)
			self.blockList.Focus(0)

	def _get_selected_block_name(self):
		sel = self.blockList.GetFirstSelected()
		if sel == -1:
			return None
		return self.blockList.GetItemText(sel)

	def _get_selected_block_data(self):
		name = self._get_selected_block_name()
		if not name:
			return None, None
		blocks = self.config["Categories"][self.currentCategory]["blocks"]
		data = blocks.get(name)
		if data:
			pinned = data.get("pinned", False)
			if isinstance(pinned, str):
				pinned = pinned.lower() == "true"
			data["pinned"] = pinned
			order = data.get("order", 0)
			try:
				order = int(order)
			except (ValueError, TypeError):
				order = 0
			data["order"] = order
		return name, data

	def _clear_inputs(self):
		self.nameCtrl.SetValue("")
		self.contentCtrl.SetValue("")
		self.editing = False
		self.editingBlockName = None
		self.editingCategory = None
		self.cancelBtn.Hide()
		self.addBtn.SetLabel(_("&Add"))
		self._update_ui_state()

	def _update_ui_state(self):
		has_block_sel = self._get_selected_block_name() is not None

		if self.editing:
			self.pasteBtn.Hide()
			self.removeBtn.Hide()
			self.moveBtn.Hide()
			self.editBtn.Hide()
			self.addBtn.Show()
			self.cancelBtn.Show()
			self.closeBtn.Show()
			self.newCatBtn.Show()
			self.newCatBtn.Enable(True)
		else:
			self.pasteBtn.Show()
			self.removeBtn.Show()
			self.moveBtn.Show()
			self.editBtn.Show()
			self.addBtn.Show()
			self.cancelBtn.Hide()
			self.closeBtn.Show()
			self.newCatBtn.Show()
			self.newCatBtn.Enable(True)

		self.pasteBtn.Enable(has_block_sel and not self.editing)
		self.removeBtn.Enable(has_block_sel and not self.editing)
		self.moveBtn.Enable(has_block_sel and len(self.config["Categories"]) > 1 and not self.editing)
		self.editBtn.Enable(has_block_sel and not self.editing)
		self.addBtn.Enable(self.currentCategory is not None)
		self.cancelBtn.Enable(self.editing)

		self.Layout()

	def _on_category_select(self, event):
		cat = self.categoryList.GetStringSelection()
		if cat and cat != self.currentCategory:
			self._select_category(cat)

	def _on_category_context_menu(self, event):
		selection = self.categoryList.GetSelection()
		if selection != wx.NOT_FOUND:
			is_all = self.categoryList.GetStringSelection() == "All"
			self.catEditItem.Enable(not is_all)
			self.catRemoveItem.Enable(not is_all)
		else:
			self.catEditItem.Enable(False)
			self.catRemoveItem.Enable(False)
		# New Category always enabled
		self.catNewItem.Enable(True)
		self.categoryList.PopupMenu(self.catContextMenu, event.GetPosition())

	def _on_new_category(self, event):
		dlg = wx.TextEntryDialog(self, _("Enter category name:"), _("New Category"))
		if dlg.ShowModal() == wx.ID_OK:
			name = dlg.GetValue().strip()
			if not name:
				wx.MessageBox(_("Category name cannot be empty."), _("Error"), wx.OK | wx.ICON_ERROR)
			elif name in self.config["Categories"]:
				wx.MessageBox(_("Category already exists."), _("Error"), wx.OK | wx.ICON_ERROR)
			else:
				self.config["Categories"][name] = {"blocks": {}}
				save_config(self.config)
				self._refresh_category_list()
				self._select_category(name)
		dlg.Destroy()

	def _on_edit_category(self, event):
		if self.currentCategory == "All":
			return
		old_name = self.currentCategory
		dlg = wx.TextEntryDialog(self, _("New name for category:"), _("Edit Category"), old_name)
		if dlg.ShowModal() == wx.ID_OK:
			new_name = dlg.GetValue().strip()
			if not new_name:
				wx.MessageBox(_("Category name cannot be empty."), _("Error"), wx.OK | wx.ICON_ERROR)
			elif new_name == old_name:
				pass
			elif new_name in self.config["Categories"]:
				wx.MessageBox(_("Category already exists."), _("Error"), wx.OK | wx.ICON_ERROR)
			else:
				self.config["Categories"][new_name] = self.config["Categories"].pop(old_name)
				save_config(self.config)
				self._refresh_category_list()
				self._select_category(new_name)
		dlg.Destroy()

	def _on_remove_category(self, event):
		if self.currentCategory == "All":
			return
		cat = self.currentCategory
		blocks = self.config["Categories"][cat]["blocks"]
		if blocks:
			wx.MessageBox(_("Cannot remove category that contains blocks. Move or delete all blocks first."),
						  _("Error"), wx.OK | wx.ICON_ERROR)
			return
		confirm = wx.MessageBox(_("Delete category '{0}'?".format(cat)),
								_("Confirm deletion"), wx.YES_NO | wx.ICON_QUESTION)
		if confirm == wx.YES:
			del self.config["Categories"][cat]
			save_config(self.config)
			self._select_category("All")
			self._update_ui_state()

	def _on_category_key_down(self, event):
		if event.GetKeyCode() == wx.WXK_DELETE and self.currentCategory != "All":
			self._on_remove_category(event)
		else:
			event.Skip()

	def _on_block_key_down(self, event):
		key = event.GetKeyCode()
		if key == wx.WXK_DELETE and self._get_selected_block_name() and not self.editing:
			self._on_remove_block(event)
		else:
			event.Skip()

	def _normalize_orders(self):
		blocks = self.config["Categories"][self.currentCategory]["blocks"]
		pinned_items = [(name, data) for name, data in blocks.items() if data.get("pinned", False)]
		unpinned_items = [(name, data) for name, data in blocks.items() if not data.get("pinned", False)]

		pinned_items.sort(key=lambda x: x[0].lower())
		unpinned_items.sort(key=lambda x: x[0].lower())

		for idx, (name, data) in enumerate(pinned_items):
			data["order"] = idx
		for idx, (name, data) in enumerate(unpinned_items):
			data["order"] = idx + len(pinned_items)

	def _refresh_and_save(self, renormalize=True):
		if renormalize:
			self._normalize_orders()
			save_config(self.config)
		self._refresh_block_list()
		selected = self._get_selected_block_name()
		if selected:
			for i in range(self.blockList.GetItemCount()):
				if self.blockList.GetItemText(i) == selected:
					self.blockList.Select(i)
					self.blockList.Focus(i)
					break

	def _on_add_block(self, event):
		name = self.nameCtrl.GetValue().strip()
		content = self.contentCtrl.GetValue()
		if not name:
			wx.MessageBox(_("Please enter a block name."), _("Error"), wx.OK | wx.ICON_ERROR)
			return

		blocks = self.config["Categories"][self.currentCategory]["blocks"]
		if not self.editing and name in blocks:
			wx.MessageBox(_("A block with this name already exists in this category."),
						  _("Error"), wx.OK | wx.ICON_ERROR)
			return

		if self.editing:
			old_name = self.editingBlockName
			old_cat = self.editingCategory
			if old_cat != self.currentCategory:
				old_blocks = self.config["Categories"][old_cat]["blocks"]
				if old_name in old_blocks:
					del old_blocks[old_name]
			else:
				if old_name != name and old_name in blocks:
					del blocks[old_name]

		blocks[name] = {
			"content": content.splitlines(),
			"pinned": False,
			"order": 0
		}
		self._refresh_and_save(renormalize=True)
		self._clear_inputs()
		ui.message(_("Success"))
		wx.CallAfter(self.blockList.SetFocus)

	def _on_edit_block(self, event):
		block_name, block_data = self._get_selected_block_data()
		if not block_name or not block_data:
			return
		content = "\n".join(block_data.get("content", []))
		self.nameCtrl.SetValue(block_name)
		self.contentCtrl.SetValue(content)
		self.editing = True
		self.editingBlockName = block_name
		self.editingCategory = self.currentCategory
		self.cancelBtn.Show()
		self.addBtn.SetLabel(_("&Save"))
		self._update_ui_state()
		self.nameCtrl.SetFocus()

	def _on_cancel_edit(self, event):
		self._clear_inputs()
		if self.blockList.GetItemCount() > 0:
			self.blockList.SetFocus()

	def _on_remove_block(self, event):
		block_name, block_data = self._get_selected_block_data()
		if not block_name:
			return
		confirm = wx.MessageBox(_("Delete block '{0}'?".format(block_name)),
								_("Confirm deletion"), wx.YES_NO | wx.ICON_QUESTION)
		if confirm == wx.YES:
			blocks = self.config["Categories"][self.currentCategory]["blocks"]
			if block_name in blocks:
				del blocks[block_name]
				self._refresh_and_save(renormalize=True)
				self._clear_inputs()
				ui.message(_("Block deleted."))

	def _on_move_block(self, event):
		block_name, block_data = self._get_selected_block_data()
		if not block_name:
			return
		other_cats = [c for c in self.config["Categories"].keys() if c != self.currentCategory]
		if not other_cats:
			return
		dlg = wx.SingleChoiceDialog(self, _("Select destination category:"),
									 _("Move Block"), other_cats)
		if dlg.ShowModal() == wx.ID_OK:
			dest_cat = dlg.GetStringSelection()
			if dest_cat == self.currentCategory:
				return
			src_blocks = self.config["Categories"][self.currentCategory]["blocks"]
			dest_blocks = self.config["Categories"][dest_cat]["blocks"]
			if block_name in src_blocks:
				dest_blocks[block_name] = src_blocks.pop(block_name)
				for cat in (self.currentCategory, dest_cat):
					self.currentCategory = cat
					self._normalize_orders()
				save_config(self.config)
				self.currentCategory = self.currentCategory
				self._refresh_category_list()
				self._select_category(self.currentCategory)
				self._clear_inputs()
				ui.message(_("Block moved to {0}.").format(dest_cat))
		dlg.Destroy()

	def _on_toggle_pin(self, event):
		block_name, block_data = self._get_selected_block_data()
		if not block_name:
			return
		current_pin = block_data.get("pinned", False)
		block_data["pinned"] = not current_pin
		self._refresh_and_save(renormalize=True)
		ui.message(_("Pinned") if not current_pin else _("Unpinned"))

	def _on_move_up(self, event):
		block_name, block_data = self._get_selected_block_data()
		if not block_name:
			return
		blocks = self.config["Categories"][self.currentCategory]["blocks"]
		order = block_data.get("order", 0)
		pinned = block_data.get("pinned", False)
		for other_name, other_data in blocks.items():
			if other_data.get("pinned", False) == pinned and other_data.get("order", 0) == order - 1:
				other_data["order"] = order
				block_data["order"] = order - 1
				self._refresh_and_save(renormalize=False)
				ui.message(_("Moved up"))
				return
		wx.Bell()

	def _on_move_down(self, event):
		block_name, block_data = self._get_selected_block_data()
		if not block_name:
			return
		blocks = self.config["Categories"][self.currentCategory]["blocks"]
		order = block_data.get("order", 0)
		pinned = block_data.get("pinned", False)
		for other_name, other_data in blocks.items():
			if other_data.get("pinned", False) == pinned and other_data.get("order", 0) == order + 1:
				other_data["order"] = order
				block_data["order"] = order + 1
				self._refresh_and_save(renormalize=False)
				ui.message(_("Moved down"))
				return
		wx.Bell()

	def _on_paste(self, event):
		block_name, block_data = self._get_selected_block_data()
		if not block_name or not block_data:
			return
		self.Hide()
		content = "\r\n".join(block_data.get("content", []))
		if len(block_data.get("content", [])) >= 2:
			content += "\r\n"

		try:
			api.copyToClip(content)
			core.callLater(100, self._do_paste)
		except Exception as e:
			log.error(f"Clipboard copy failed: {e}")
			wx.MessageBox(_("Failed to copy to clipboard."), _("Error"), wx.OK | wx.ICON_ERROR)
			self.Destroy()

	def _do_paste(self):
		focus = api.getFocusObject()
		try:
			if hasattr(focus, "windowClassName") and focus.windowClassName == "ConsoleWindowClass":
				watchdog.cancellableSendMessage(focus.windowHandle, 0x0111, 0xfff1, 0)
			elif hasattr(focus, "windowClassName") and "Rich" in focus.windowClassName and "Text" in focus.windowClassName:
				watchdog.cancellableSendMessage(focus.windowHandle, 0x0302, 0, 0)
			else:
				KeyboardInputGesture.fromName("control+v").send()
		except Exception as e:
			log.error(f"Paste failed: {e}")
			wx.MessageBox(_("Failed to paste. Please use Ctrl+V manually."), _("Error"), wx.OK | wx.ICON_ERROR)
		core.callLater(50, self.Destroy)

	def _on_block_context_menu(self, event):
		if self.blockList.GetFirstSelected() != -1:
			block_name, block_data = self._get_selected_block_data()
			if block_data:
				is_pinned = block_data.get("pinned", False)
				self.blockPinItem.SetItemLabel(_("Unpin") if is_pinned else _("Pin"))
				self.blockSaveItem.Enable(self.editing)
				self.blockEditItem.Enable(not self.editing)
				self.blockMoveUpItem.Enable(not self.editing)
				self.blockMoveDownItem.Enable(not self.editing)
			self.blockList.PopupMenu(self.blockContextMenu, event.GetPosition())
		else:
			event.Skip()

	def _on_close(self, event):
		self.Destroy()