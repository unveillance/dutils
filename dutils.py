import re, os, json
from sys import stdin
from fabric.api import settings, local

from conf import BASE_DIR, __load_config, save_config

def generate_run_routine(config=None, dest_d=None, src_dirs=None):
	if config is None:
		config = __load_config(BASE_DIR, "config.json")

	if 'PUBLISH_PORTS' not in config.keys():
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(IMAGE_NAME)s:latest"
	else:
		p_sep = " -p "
		config['PUBLISH_PORTS_STR'] = ("%s%s" % (p_sep, p_sep.join(["%d:%d" % (p, p) for p in config['PUBLISH_PORTS']])))[1:]
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(PUBLISH_PORTS_STR)s %(IMAGE_NAME)s:latest"
	
	try:
		d_info = json.loads(stdin)[0]['HostConfig']['PortBindings']
		mapped_ports = [] if 'PUBLISH_PORTS' not in config.keys() else config['PUBLISH_PORTS']
		port_bindings = []

		for p in d_info.keys():
			port = int(re.findall(r'(\d+)/tcp', p)[0])
			mapping = int(d_info[p][0]['HostPort'])

			if port in mapped_ports:
				mapping = port

			port_bindings.append([port, mapping])

		config['PORT_BINDINGS_STR'] = ", ".join(["%d > %d" % (p[0], p[1]) for p in port_bindings])

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
			"\tif [[ $1 == \"shell\" ]]; then",
			("\t\t%s /bin/bash" % r).replace("-dPt", "-iPt"),
			"\telif [[ $1 == \"update\" ]]; then",
			"\t\t./update.sh",
			"\t\texit",
			"\tfi",
			"fi"
		]

		if generate_update_routine(config, src_dirs=src_dirs):
			return build_routine([r % config for r in routine], dest_d=os.path.join(BASE_DIR, "run.sh") if dest_d is None else dest_d)
	
	except Exception as e:
		print e, type(e)

	return False

def generate_shutdown_routine(config=None, dest_d=None):
	if config is None:
		config = __load_config(BASE_DIR, "config.json")

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
		
		return build_routine([r % config for r in routine], dest_d=os.path.join(BASE_DIR, "shutdown.sh") if dest_d is None else dest_d)
	except Exception as e:
		print e, type(e)

	return False

def generate_init_routine(config, dest_d=None):
	if 'DOCKER_EXE' not in config.keys():
		config['DOCKER_EXE'] = get_docker_exe()

	if config['DOCKER_EXE'] is None:
		print "no docker exe."
		return False

	try:
		routine = [
			"%(DOCKER_EXE)s build -t %(IMAGE_NAME)s:init .",
			"%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -iPt %(IMAGE_NAME)s:init",
			"echo \"Commiting image.  This might take awhile...\"",
			"%(DOCKER_EXE)s commit %(IMAGE_NAME)s %(IMAGE_NAME)s:init",
			"%(DOCKER_EXE)s stop %(IMAGE_NAME)s",
			"%(DOCKER_EXE)s rm %(IMAGE_NAME)s"
		]

		del config['USER_PWD']
		save_config(config)

		return build_routine([r % config for r in routine], dest_d=dest_d)
	except Exception as e:
		print e, type(e)

	return False

def generate_build_routine(config, dest_d=None):
	if 'DOCKER_EXE' not in config.keys():
		config['DOCKER_EXE'] = get_docker_exe()

	if config['DOCKER_EXE'] is None:
		print "no docker exe."
		return False

	try:
		routine = [
			"%(DOCKER_EXE)s build -t %(IMAGE_NAME)s:latest .",
			"%(DOCKER_EXE)s rmi %(IMAGE_NAME)s:init",
			"%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(IMAGE_NAME)s:latest",
			"echo $(%(DOCKER_EXE)s inspect %(IMAGE_NAME)s) | python %(COMMIT_TO)s.py commit",
			"%(DOCKER_EXE)s commit %(IMAGE_NAME)s %(IMAGE_NAME)s:latest",
			"%(DOCKER_EXE)s stop %(IMAGE_NAME)s",
			"%(DOCKER_EXE)s rm %(IMAGE_NAME)s"
		]

		return build_routine([r % config for r in routine], dest_d=dest_d)
	except Exception as e:
		print e, type(e)

	return False

def generate_update_routine(config, dest_d=None, src_dirs=None):
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
			"python %(COMMIT_TO)s.py update",
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

		return build_routine([r % config for r in routine], dest_d=os.path.join(BASE_DIR, "update.sh") if dest_d is None else dest_d)

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

def build_routine(routine, to_file=None, dest_d=None):
	if to_file is None:
		to_file = os.path.join(BASE_DIR, ".routine.sh") if dest_d is None else dest_d

	try:
		with open(to_file, 'wb+') as r:
			r.write("\n".join(routine))
		
		return True

	except Exception as e:
		print e, type(e)

	return False