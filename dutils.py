import re, os

def build_dockerfile(src_d, config, dest_d=None):
	if dest_d is None:
		dest_d = os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir))

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

		with open(os.path.join(dest_d, "Dockerfile"), 'wb+') as d:
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

	return docker

def build_routine(routine, dest_d=None):
	if dest_d is None:
		dest_d = os.path.abspath(os.path.join(os.path.join(__file__, os.pardir), os.pardir))
		
	try:
		with open(os.path.join(dest_d, ".routine.sh"), 'wb+') as r:
			r.write("\n".join(routine))
		
		return True

	except Exception as e:
		print e, type(e)

	return False