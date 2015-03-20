import re, os, json
from fabric.api import settings, local

from conf import BASE_DIR, __load_config, save_config, append_to_config

def validate_private_key(ssh_priv_key, with_config):
	config = __load_config(os.path.join(BASE_DIR, "config.json") if with_config is None else with_config)

	if ssh_priv_key is None:
		ssh_priv_key = os.path.join(BASE_DIR, "%s.privkey" % config['IMAGE_NAME'])

	if not os.path.exists(ssh_priv_key):
		from fabric.operations import prompt
		ssh_priv_key_pwd = prompt("Give a password to your ssh key (or ENTER for no password)")

		if len(ssh_priv_key_pwd) == 0:
			ssh_priv_key_pwd = "\"\""

		with settings(warn_only=True):
			local("ssh-keygen -f %s -t rsa -b 4096 -N %s" % (ssh_priv_key, ssh_priv_key_pwd))

	ssh_pub_key = "%s.pub" % ssh_priv_key
	if not os.path.exists(ssh_priv_key) or not os.path.exists(ssh_pub_key):
		print "Sorry, there is no key made at %s" % ssh_priv_key
		return None

	return append_to_config({
		'SSH_PUB_KEY' : os.path.abspath(ssh_pub_key),
		'SSH_PRIV_KEY' : os.path.abspath(ssh_priv_key)
	}, with_config=with_config)

def parse_ports(config):
	try:
		with settings(warn_only=True):
			d_info = local("%(DOCKER_EXE)s inspect %(IMAGE_NAME)s" % config, capture=True)

		d_info = json.loads(d_info)[0]['HostConfig']['PortBindings']
	except Exception as e:
		print "could not get any stdin."
		print e, type(e)
		return config, None

	mapped_ports = [] if 'PUBLISH_PORTS' not in config.keys() else config['PUBLISH_PORTS']
	port_bindings = []

	for p in d_info.keys():
		port = int(re.findall(r'(\d+)/tcp', p)[0])
		mapping = int(d_info[p][0]['HostPort'])

		if port == 22:
			config['SSH_PORT'] = mapping

		if port in mapped_ports:
			mapping = port

		port_bindings.append([port, mapping])

	config['PORT_BINDINGS_STR'] = ", ".join(["%d > %d" % (p[0], p[1]) for p in port_bindings])

	return config, d_info

def resolve_publish_ports(publish_ports):
	p_sep = " -p "
	return ("%s%s" % (p_sep, p_sep.join(publish_ports)))[1:]

def finalize_assets(with_config=None):
	if with_config is None:
		dir_root = BASE_DIR
	else:
		dir_root = os.path.dirname(with_config)

	try:
		with settings(warn_only=True):
			local("cp dutils/stop.sh %s" % dir_root)
			for f in ['run', 'update', 'shutdown', 'stop']:
				if os.path.exists(os.path.join(dir_root, "%s.sh" % f)):
					local("chmod +x %s" % os.path.join(dir_root, "%s.sh" % f))
		return True
		
	except Exception as e:
		print e, type(e)

	return False

def generate_run_routine(config, with_config=None, src_dirs=None):
	if 'PUBLISH_PORTS' not in config.keys():
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(IMAGE_NAME)s:latest"
	else:
		if 'PUBLISH_PORTS_STR' not in config.keys():
			config['PUBLISH_PORTS_STR'] = resolve_publish_ports(config['PUBLISH_PORTS'])

		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(PUBLISH_PORTS_STR)s %(IMAGE_NAME)s:latest"
	
	try:
		config, d_info = parse_ports(config)

		routine = [
			"%(DOCKER_EXE)s ps -a | grep %(IMAGE_NAME)s",
			"if ([ $? -eq 0 ]); then",
			"\techo \"Stopping current instance first.\"",
			"\t./stop.sh",
			"fi",
			"if ([ $# -eq 0 ]); then",
			"\t%s ./run.sh" % r,
			"\techo \"%(IMAGE_NAME)s has started.\"",
			"\techo \"ip address: %(DOCKER_IP)s\"",
			"\techo \"port mappings: %(PORT_BINDINGS_STR)s\"",
			"else",
			"\tif [[ $1 == \"shell\" ]]; then"
		]

		if 'SSH_PRIV_KEY' not in config.keys() or 'SSH_PORT' not in config.keys():
			routine.append(("\t\t%s /bin/bash" % r).replace("-dPt", "-iPt"))
		else:
			ssh_routine = [
				"\t\t%s ./run.sh" % r,
				"\t\tsleep 5",
				"\t\tssh -o IdentitiesOnly=yes -i %(SSH_PRIV_KEY)s -p %(SSH_PORT)d %(USER)s@%(DOCKER_IP)s"
			]

			routine += ssh_routine

		routine += [
			"\telif [[ $1 == \"update\" ]]; then",
			"\t\t./update.sh",
			"\t\texit",
			"\tfi",
			"fi"
		]

		save_config(config, with_config=with_config)

		if generate_update_routine(config, src_dirs=src_dirs, with_config=with_config):
			return build_routine([r % config for r in routine], to_file=os.path.join(BASE_DIR if with_config is None else os.path.dirname(with_config), "run.sh"))
	
	except Exception as e:
		print e, type(e)

	return False

def generate_shutdown_routine(config, with_config=None):
	try:
		routine = [
			"echo $1 | grep y",
			"if ([ $? -eq 0 ]); then",
			"\t%(DOCKER_EXE)s start %(IMAGE_NAME)s",
			"\t%(DOCKER_EXE)s commit %(IMAGE_NAME)s %(IMAGE_NAME)s:latest",
			"fi",
			"%(DOCKER_EXE)s stop %(IMAGE_NAME)s",
			"%(DOCKER_EXE)s rm %(IMAGE_NAME)s"
		]
		
		return build_routine([r % config for r in routine], to_file=os.path.join(BASE_DIR if with_config is None else os.path.dirname(with_config), "shutdown.sh"))
	except Exception as e:
		print e, type(e)

	return False

def generate_init_routine(config, with_config=None):
	if 'DOCKER_EXE' not in config.keys():
		config['DOCKER_EXE'] = get_docker_exe()

	if config['DOCKER_EXE'] is None:
		print "no docker exe."
		return False

	if 'PUBLISH_PORTS' not in config.keys():
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -iPt %(IMAGE_NAME)s:init"
	else:
		if 'PUBLISH_PORTS_STR' not in config.keys():
			config['PUBLISH_PORTS_STR'] = resolve_publish_ports(config['PUBLISH_PORTS'])
			
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -iPt %(PUBLISH_PORTS_STR)s %(IMAGE_NAME)s:init"

	try:
		routine = [
			"%(DOCKER_EXE)s build -t %(IMAGE_NAME)s:init .",
			r,
			"echo \"Commiting image.  This might take awhile...\"",
			"%(DOCKER_EXE)s commit %(IMAGE_NAME)s %(IMAGE_NAME)s:init",
			"%(DOCKER_EXE)s stop %(IMAGE_NAME)s",
			"%(DOCKER_EXE)s rm %(IMAGE_NAME)s"
		]

		if 'SSH_PUB_KEY' in config.keys():
			ssh_routine = [
				"mkdir src/.ssh",
				"cp %(SSH_PUB_KEY)s src/.ssh/authorized_keys"
			]

			routine = ssh_routine + routine

		if 'USER_PWD' in config.keys():
			del config['USER_PWD']
		else:
			print "NO USER PWD"
		
		save_config(config, with_config=with_config)

		return build_routine([r % config for r in routine])
	except Exception as e:
		print e, type(e)

	return False

def generate_build_routine(config, with_config=None):
	if 'DOCKER_EXE' not in config.keys():
		config['DOCKER_EXE'] = get_docker_exe()

	if config['DOCKER_EXE'] is None:
		print "no docker exe."
		return False

	if 'PUBLISH_PORTS' not in config.keys():
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(IMAGE_NAME)s:latest"
	else:
		if 'PUBLISH_PORTS_STR' not in config.keys():
			config['PUBLISH_PORTS_STR'] = resolve_publish_ports(config['PUBLISH_PORTS'])

		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(PUBLISH_PORTS_STR)s %(IMAGE_NAME)s:latest"

	c = "python %(COMMIT_TO)s.py commit" % config
	if with_config is not None:
		c = "%s %s" % (c, with_config)

	try:
		routine = [
			"%(DOCKER_EXE)s build -t %(IMAGE_NAME)s:latest .",
			"%(DOCKER_EXE)s rmi %(IMAGE_NAME)s:init",
			r,
			c,
			"%(DOCKER_EXE)s commit %(IMAGE_NAME)s %(IMAGE_NAME)s:latest",
			"%(DOCKER_EXE)s stop %(IMAGE_NAME)s",
			"%(DOCKER_EXE)s rm %(IMAGE_NAME)s"
		]

		return build_routine([r % config for r in routine])
	except Exception as e:
		print e, type(e)

	return False

def generate_update_routine(config, with_config=None, src_dirs=None):
	config['WITH_CONFIG'] = os.path.join(BASE_DIR, "config.json") if with_config is None else with_config

	try:
		routine = [
			"THIS_DIR=$(pwd)",
			"EXPRESS_DIR=%s" % BASE_DIR,
			"./stop.sh"
		]

		if src_dirs is not None:
			if type(src_dirs) in [str, unicode]:
				src_dirs = [src_dirs]

		if type(src_dirs) is list:
			for src_dir in src_dirs:
				routine.append("cd $EXPRESS_DIR/src/%s && git pull origin master" % src_dir)

		routine += [
			"cd $EXPRESS_DIR",
			"source venv/bin/activate",
			"python %(COMMIT_TO)s.py update %(WITH_CONFIG)s",
			"if ([ $? -eq 0 ]); then",
			"\t%(DOCKER_EXE)s build -t %(IMAGE_NAME)s:latest .",
			"\trm Dockerfile",
			"\t%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -iPt %(IMAGE_NAME)s:latest ./update.sh",
			"\t%(DOCKER_EXE)s commit %(IMAGE_NAME)s %(IMAGE_NAME)s:latest",
			"\t%(DOCKER_EXE)s stop %(IMAGE_NAME)s",
			"\t%(DOCKER_EXE)s rm %(IMAGE_NAME)s",
			"fi",
			"deactivate venv",
			"cd $THIS_DIR"
		]

		return build_routine([r % config for r in routine], to_file=os.path.join(BASE_DIR if with_config is None else os.path.dirname(with_config), "update.sh"))

	except Exception as e:
		print e, type(e)

	return False

def build_bash_profile(directives, dest_d=None):
	try:
		with open(os.path.join(BASE_DIR if dest_d is None else dest_d, ".bash_profile"), 'wb+') as B:
			B.write("\n".join(directives))
		return True
	
	except Exception as e:
		print e, type(e)

	return False

def build_dockerfile(src_dockerfile, config, dest_d=None):
	dockerfile = []
	rx = re.compile("\$\{(%s)\}" % "|".join(config.keys()))

	try:
		with open(src_dockerfile, 'rb') as d:
			for line in d.read().splitlines():
				for e in re.findall(rx, line):
					try:
						line = line.replace("${%s}" % e, str(config[e]))
					except Exception as ex:
						print e, ex, type(ex)

				dockerfile.append(line)

		with open(os.path.join(BASE_DIR if dest_d is None else dest_d, "Dockerfile"), 'wb+') as d:
			d.write("\n".join(dockerfile))
		
		return True

	except Exception as e:
		print e, type(e)

	return False

def get_docker_exe():
	with settings(warn_only=True):
		docker = local("which docker", capture=True)

	if len(docker) == 0:
		from fabric.operations import prompt

		print "Do you have docker installed?"
		docker = prompt("If so, what is its path?")

		if len(docker) == 0:
			print "No Docker to use!  Please install docker!"
			return None

	with settings(warn_only=True):
		uname = local("uname", capture=True)
		if uname == "Linux":
			docker = "sudo %s" % docker

	return docker

def get_docker_ip():
	docker_ip = "127.0.0.1"

	with settings(warn_only=True):
		uname = local("uname", capture=True)

		if uname != "Linux":
			docker_ip = local("echo $(boot2docker ip)", capture=True)

	return docker_ip

def build_routine(routine, to_file=None):
	if to_file is None:
		to_file = os.path.join(BASE_DIR, ".routine.sh")

	try:
		with open(to_file, 'wb+') as r:
			r.write("\n".join(routine))
		
		return True

	except Exception as e:
		print e, type(e)

	return False