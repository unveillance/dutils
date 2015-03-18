#! /bin/bash

echo "Shutting down.  Save state? [y|N]: "
read $SAVE_STATE

./shutdown.sh $SAVE_STATE
echo "Stopped."