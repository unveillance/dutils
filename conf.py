import os, json
from collections import namedtuple
from fabric.operations import prompt

BASE_DIR = os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir))
DUtilKey = namedtuple("DUtilKey", ["label", "description", "default", "default_str", "value_transform"])

SUS_RANDO = "sus_rando"
BEEP_BOP = "beepBop"
DDOC_NAME = "my_docker_image"

DUtilKeyDefaults = {
	'USER' : DUtilsKey("USER", "system user", SUS_RANDO, SUS_RANDO, None),
	'USER_PWD' : DUtilsKey("USER_PWD", "system user's password", BEEP_BOP, BEEP_BOP, None),
	'IMAGE_NAME' : DUtilsKey("IMAGE_NAME", "name of docker image", DDOC_NAME, DDOC_NAME, None)
}

def build_config(config_keys, with_config=None):
	config = {}

	if with_config is not None:
		if not os.path.exists(with_config):
			print "cannot find file at %s" % with_config
			print "Not a valid config file"

		else:
			try:
				with open(with_config, 'rb') as c:
					config = json.loads(c.read())
			except Exception as e:
				print e, type(e)
				print "Not a valid config file"

	for c in config_keys:
		if c.label not in config.keys():
			print c.description
			value = prompt("[ENTER for default ( %s )]: " % c.default)

			if len(value) > 0:
				config[c.label] = value if c.value_transform is None else c.value_transform(value)
			else:
				config[c.label] = c.default

	return config

def save_config(with_config, to_file=None):
	if to_file is None:
		to_file = os.path.join(BASE_DIR, "config.json")

	try:
		with open(to_file, 'wb+') as c:
			c.write(json.dumps(with_config))

		return True
	except Exception as e:
		print "COULD NOT SAVE CONFIG:"
		print e, type(e)

	return False

def __append_to_config(append_to_config, to_file=None, return_config=False):
	if to_file is None:
		to_file = os.path.join(BASE_DIR, "config.json")

	try:
		with open(to_file, 'rb') as c:
			config = json.loads(c.read())
			config.update(append_to_config)

		with open(to_file, 'wb+') as c:
			c.write(json.dumps(config))

		if return_config:
			return True, config

		return True
	except Exception as e:
		print e, type(e)

	return False

def __load_config(with_config):
	try:
		with open(with_config, 'rb') as c:
			return json.loads(c.read())
	except Exception as e:
		print e, type(e)
	
	return None

def get_config(keys, with_config=None):
	if with_config is None:
		with_config = os.path.join(BASE_DIR, "config.json")

	if type(with_config) not in [dict, str, unicode]:
		return None

	if type(with_config) in [str, unicode]:
		with_config = __load_config(with_config)

	if with_config is None:
		return False

	try:
		if type(keys) in [str, unicode]:
			return with_config[keys]
		elif type(keys) is list:
			return [with_config[key] for key in keys]
	except Exception as e:
		try:
			print e, type(e)
		except Exception as e_:
			print  e, type(e)

	return None