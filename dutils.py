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