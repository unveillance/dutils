#! /bin/bash

# example: dutils/setup.sh compass_express /path/to/config.json --nginx-conf=/path/to/an/nginx/template.conf

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
shift
echo "$@"

THIS_DIR=`pwd`
DUTILS_DIR=$(cd "$(dirname "{BASH_SOURCE[0]}")" && pwd)
echo $DUTILS_DIR
cd $DUTILS_DIR

# Create virtualenv
virtualenv venv
source venv/bin/activate

# Install python requirements
pip install -r dutils/requirements.txt

# Run Docker init
declare -a D_ROUTINES=("init" "build" "finish")
for DR in "${D_ROUTINES[@]}"; do
	python $DUTILS_PKG_ROOT.py $DR "$@"
	if ([ $?  -eq 0 ]); then
		run_docker_routine
		echo "Moving on!"
	else
		echo "FAILED."
		do_exit
	fi
done

cd $THIS_DIR
do_exit