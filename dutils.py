import re, os, json
from sys import stdin
from fabric.api import settings, local

from conf import BASE_DIR, __load_config, save_config

def generate_run_routine(config=None, dest_d=None):
	if config is None:
		config = __load_config(BASE_DIR, "config.json")

	if 'PUBLISH_PORTS' not in config['keys']:
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(IMAGE_NAME)s:latest"
		config['PUBLISH_PORTS'] = "None"
	else:
		r = "%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(PUBLISH_PORTS)s %(IMAGE_NAME)s:latest"
	
	try:
		d_info = json.loads(stdin.read())[0]['HostConfig']['PortBindings']
		published_ports = []
		
		print d_info
		
		for p in d_info.keys():
			published_ports.append([int(re.match(r'(\d+)/tcp', p).group()), int(d_info[p][0]['HostPort'])])

		config['PUBLISHED_PORTS_STR'] = ", ".join(["%d > %d" % (p, p) for p in published_ports])[1:]

		routine = [
			"%(DOCKER_EXE)s ps -a | grep %(IMAGE_NAME)s",
			"if ([ $? -eq 0 ]); then",
			"\techo \"Stopping current instance first.\"",
			"\t./stop.sh",
			"fi",
			r,
			"echo \"%(IMAGE_NAME)s has started.\"",
			"echo \"ip address: %(DOCKER_IP)s\"",
			"echo \"port mappings: %(PUBLISHED_PORTS_STR)s\""
		]

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

def generate_build_routine(config, commit_to, dest_d=None):
	if 'DOCKER_EXE' not in config.keys():
		config['DOCKER_EXE'] = get_docker_exe()

	if config['DOCKER_EXE'] is None:
		print "no docker exe."
		return False

	config['COMMIT_TO'] = commit_to

	try:
		routine = [
			"%(DOCKER_EXE)s build -t %(IMAGE_NAME)s:latest .",
			"%(DOCKER_EXE)s rm %(IMAGE_NAME)s",
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