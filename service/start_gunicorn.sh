#!/bin/bash
set -e
LOGFILE=/Users/drozdovsky/workspace/conqueror/service/logs/conqueror.log
LOGDIR=$(dirname $LOGFILE)
NUM_WORKERS=2

# PID file
PIDFILE="$HOME/tmp/conqueror_service.pid"

# check if gunicorn for this site is already running
if [ -e "${PIDFILE}" ] && (ps -u $USER -f | grep "[ ]$(cat ${PIDFILE})[ ]"); then
  echo "Already running."
  exit 99
fi

# user/group to run as
USER=drozdovsky
GROUP=admin

# activate virtualenv and test log directory
source /Users/drozdovsky/.envs/conqueror/bin/activate
test -d $LOGDIR || mkdir -p $LOGDIR
cd /Users/drozdovsky/workspace/conqueror/service/

export PATH=$PATH:/Users/drozdovsky/workspace/conqueror/service/conqueror/
export PYTHONPATH=$PYTHONPATH:/Users/drozdovsky/workspace/conqueror/service/conqueror/
#exec python

# run gunicorn
exec /Users/drozdovsky/.envs/conqueror/bin/gunicorn -b 127.0.0.1:8041 -w $NUM_WORKERS --user=$USER --group=$GROUP --max-requests=200 --log-level=debug --log-file=$LOGFILE 2>>$LOGFILE conqueror.app:app
