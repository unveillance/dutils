#! /bin/bash

# example: dutils/setup.sh compass_express /path/to/config.json

function run_docker_routine {
	chmod +x .routine.sh
	./.routine.sh
	rm .routine.sh
}

function do_exit {
	deactivate venv
	exit
}

DUTILS_PKG_ROOT=$1

# Create virtualenv
virtualenv venv
source venv/bin/activate

# Install python requirements
pip install -r dutils/requirements.txt

# Run Docker init
declare -a D_ROUTINES=("init $2" "build" "commit")
for DR in "${D_ROUTINES[@]}"; do
	python $DUTILS_PKG_ROOT.py $DR
	if ([ $?  -eq 0 ]); then
		run_docker_routine
	else
		echo "FAILED."
		do_exit
	fi
done

cp dutils/stop.sh .
chmod +x run.sh
chmod +x shutdown.sh
chmod +x update.sh

do_exit