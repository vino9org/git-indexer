#!/bin/sh

ENV_FILE=/etc/secret-volume/env

if [ -f "$ENV_FILE" ]; then
    echo "source $ENV_FILE"
    export $(grep -v -e "^#" $ENV_FILE | xargs)
fi

# automatically restart gunicorn if it crashes for whatever reason
while true
do
    gunicorn -w 1 git_search:app  --bind 0.0.0.0:8000
    sleep 3
done
