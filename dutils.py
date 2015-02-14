import re, os
from conf import BASE_DIR

def generate_init_routine(config, dest_d=None):
	if 'DOCKER_EXE' not in config.keys():
		config['DOCKER_EXE'] = get_docker_exe()

	if config['DOCKER_EXE'] is None:
		print "no docker exe."
		return False

	try:
		routine = [
			"%(DOCKER_EXE)s build -t %(STUB_IMAGE)s .",
			"%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -it %(STUB_IMAGE)s",
			"%(DOCKER_EXE)s commit %(IMAGE_NAME)s %(STUB_IMAGE)s",
			"%(DOCKER_EXE)s stop %(IMAGE_NAME)s"
		]

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
			"%(DOCKER_EXE)s build -t %(FINAL_IMAGE)s .",
			"%(DOCKER_EXE)s rm %(IMAGE_NAME)s",
			"%(DOCKER_EXE)s rmi %(STUB_IMAGE)s",
			"%(DOCKER_EXE)s run --name %(IMAGE_NAME)s -dPt %(FINAL_IMAGE)s",
			"echo $(%(DOCKER_EXE)s inspect %(IMAGE_NAME)s) | python %(COMMIT_TO)s.py commit",
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

def build_dockerfile(src_d, config, dest_d=None):
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
	from fabric.api import settings, local

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

def build_routine(routine, to_file=None, dest_d=None):
	if to_file is None:
		to_file = os.path.join(BASE_DIR if dest_d is None else dest_d, ".routine.sh")

	try:
		with open(to_file, 'wb+') as r:
			r.write("\n".join(routine))
		
		return True

	except Exception as e:
		print e, type(e)

	return False