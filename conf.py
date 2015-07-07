import os, json, re, getpass
from collections import namedtuple
from fabric.operations import prompt

BASE_DIR = os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir))
DUtilsKey = namedtuple("DUtilsKey", ["label", "description", "default", "default_str", "value_transform"])

SUS_RANDO = "sus_rando"
BEEP_BOP = "beepBop"
DDOC_NAME = "my_docker_image"

DUtilsKeyDefaults = {
	'USER' : DUtilsKey("USER", "system user", SUS_RANDO, SUS_RANDO, None),
	'USER_PWD' : DUtilsKey("USER_PWD", "system user's password", BEEP_BOP, BEEP_BOP, None),
	'IMAGE_NAME' : DUtilsKey("IMAGE_NAME", "name of docker image", DDOC_NAME, DDOC_NAME, None),
}

DUtilsTransforms = {
	'PORT_TO_INT' : lambda p : int(p.strip()),
	'NONE_IF_EMPTY' : lambda s : None if len(s) == 0 else s
}

def is_acceptable_str(str):
	try:
		return re.match(r'.*[\s]+', str) is None
	except Exception as e:
		print e, type(e)

	return False

def get_directive(args, flags):
	if type(flags) in [str, unicode]:
		flags = [flags]

	if type(flags) is not list:
		return None

	directives = []
	if len(args) >= 2:
		for a in args[1:]:
			if re.match(r'^\-\-', a) is None:
				continue

			directive = a.split("=")
			if directive[0][2:] in flags:
				directives.append(directive[1])

	if len(directives) == 0:
		return None
	elif len(directives) == 1:
		directives = directives[0]

	return directives

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
			prompt_ = "[ENTER for default ( %s )]: " % c.default

			'''
			i don't yet have a glamourous way of discerning whether 
			a config key should be treated as a password yet.
			so for now, it's a whitelist.
			'''
			
			if c.label not in ["USER_PWD"]:
				value = prompt(prompt_)
			else:
				value = capture_pwd(c, prompt_)

			if len(value) > 0:
				if c.value_transform is None:
					if not is_acceptable_str(value.strip()):
						value = c.default

				else:
					value = c.value_transform(value)

				config[c.label] = value
			else:
				print "USING DEFAULT: %s" % c.default
				config[c.label] = c.default

	return config

def capture_pwd(config_key, prompt_):
	value = getpass(prompt_)
	if len(value) == 0:
		return value

	confirm_value = getpass("Confirm %s" % config_key.label)

	if value == confirm_value:
		return value

	print "TRY AGAIN! %s must match!" % config_key.label
	return capture_pwd(config_key, prompt_)

def save_config(config, with_config=None):
	if with_config is None:
		with_config = os.path.join(BASE_DIR, "config.json")

	try:
		with open(with_config, 'wb+') as c:
			c.write(json.dumps(config))

		return True
	except Exception as e:
		print "COULD NOT SAVE CONFIG:"
		print e, type(e)

	return False

def append_to_config(append_to_config, with_config=None, return_config=False):
	if with_config is None:
		with_config = os.path.join(BASE_DIR, "config.json")

	try:
		with open(with_config, 'rb') as c:
			config = json.loads(c.read())
			config.update(append_to_config)

		with open(with_config, 'wb+') as c:
			c.write(json.dumps(config))

		if return_config:
			return True, config

		return True
	except Exception as e:
		print e, type(e)

	return False

def __load_config(with_config=None):
	if with_config is None:
		with_config = os.path.join(BASE_DIR, "config.json")
		
	try:
		with open(with_config, 'rb') as c:
			return json.loads(c.read())
	except Exception as e:
		print "__load_config Error:"
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