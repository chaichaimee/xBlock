# config.py

import os
import globalVars
from configobj import ConfigObj
from logHandler import log

old_config_path = os.path.join(globalVars.appArgs.configPath, "xBlock.ini")
new_config_dir = os.path.join(globalVars.appArgs.configPath, "ChaiChaimee")
new_config_path = os.path.join(new_config_dir, "xBlock.ini")

os.makedirs(new_config_dir, exist_ok=True)

def _ensure_correct_structure(config):
	changed = False
	if "Categories" not in config:
		config["Categories"] = {"All": {"blocks": {}}}
		changed = True
		log.info("xBlock: Added missing 'Categories'")
	elif "All" not in config["Categories"]:
		config["Categories"]["All"] = {"blocks": {}}
		changed = True
		log.info("xBlock: Added missing 'All' category")
	for cat in config["Categories"]:
		if "blocks" not in config["Categories"][cat]:
			config["Categories"][cat]["blocks"] = {}
			changed = True
			log.info("xBlock: Added missing 'blocks' in category '%s'", cat)
	if "blocks" in config:
		del config["blocks"]
		changed = True
		log.info("xBlock: Removed obsolete root 'blocks'")
	if "version" not in config:
		config["version"] = "2"
		changed = True
	return changed

def _convert_blocks(blocks_dict):
	new_blocks = {}
	order_counter = 0
	for name, value in blocks_dict.items():
		if isinstance(value, dict) and "content" in value:
			content = value["content"]
			pinned = value.get("pinned", False)
			if isinstance(pinned, str):
				pinned = pinned.lower() == "true"
			order = value.get("order", 0)
			try:
				order = int(order)
			except (ValueError, TypeError):
				order = order_counter
		else:
			if isinstance(value, list):
				content = value
			elif isinstance(value, str):
				content = value.splitlines()
			else:
				content = [str(value)]
			pinned = False
			order = order_counter
		new_blocks[name] = {
			"content": content,
			"pinned": pinned,
			"order": order
		}
		order_counter += 1
	return new_blocks

def _migrate_from_old():
	if not os.path.isfile(old_config_path):
		log.info("xBlock: No old config at %s", old_config_path)
		return None

	log.info("xBlock: Found old config at %s", old_config_path)
	try:
		old_config = ConfigObj(old_config_path, encoding='utf-8', list_values=True)
	except Exception as e:
		log.error("xBlock: Failed to read old config: %s", e)
		return None

	if not old_config:
		log.warning("xBlock: Old config is empty")
		return None

	if "Categories" in old_config:
		log.info("xBlock: Old config already has Categories structure")
		for cat in old_config["Categories"]:
			if "blocks" in old_config["Categories"][cat]:
				old_config["Categories"][cat]["blocks"] = _convert_blocks(
					old_config["Categories"][cat]["blocks"]
				)
			else:
				old_config["Categories"][cat]["blocks"] = {}
		if "All" not in old_config["Categories"]:
			old_config["Categories"]["All"] = {"blocks": {}}
		new_config = ConfigObj(encoding='utf-8')
		new_config.update(old_config)
		if "blocks" in new_config:
			del new_config["blocks"]
		new_config["version"] = "2"
		log.info("xBlock: Migrated existing Categories")
		return new_config

	if "blocks" not in old_config:
		log.warning("xBlock: Old config has no 'blocks' key and no Categories")
		return None

	old_blocks = old_config["blocks"]
	if not isinstance(old_blocks, dict):
		log.warning("xBlock: Old blocks is not a dict: %s", type(old_blocks))
		return None

	block_count = len(old_blocks)
	log.info("xBlock: Found %d blocks in old config", block_count)

	converted_blocks = _convert_blocks(old_blocks)

	new_config = ConfigObj(encoding='utf-8')
	new_config["Categories"] = {"All": {"blocks": converted_blocks}}
	new_config["version"] = "2"
	log.info("xBlock: Migration complete, converted %d blocks", block_count)
	return new_config

def get_config():
	if os.path.isfile(new_config_path):
		log.info("xBlock: Loading existing config from %s", new_config_path)
		config = ConfigObj(new_config_path, encoding='utf-8', list_values=True)
		if config is None:
			config = ConfigObj(encoding='utf-8')
			config.filename = new_config_path

		changed = _ensure_correct_structure(config)
		for cat in config["Categories"]:
			if "blocks" in config["Categories"][cat]:
				config["Categories"][cat]["blocks"] = _convert_blocks(
					config["Categories"][cat]["blocks"]
				)
				changed = True
			else:
				config["Categories"][cat]["blocks"] = {}
				changed = True
		if changed:
			config.write()
		return config

	log.info("xBlock: No config at %s, checking old location", new_config_path)
	migrated = _migrate_from_old()
	if migrated is not None:
		migrated.filename = new_config_path
		_ensure_correct_structure(migrated)
		migrated.write()
		log.info("xBlock: Migrated config saved to %s", new_config_path)
		return migrated

	log.info("xBlock: Creating fresh config")
	config = ConfigObj(encoding='utf-8')
	config["Categories"] = {"All": {"blocks": {}}}
	config["version"] = "2"
	config.filename = new_config_path
	config.write()
	return config

def save_config(config):
	config.write()
	log.debug("xBlock: Config saved")