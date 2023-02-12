#!/bin/sh

echo "starting dataserver entrypoint script"

if [ ! -f /opt/mcds/datadb/data.db ]
then
    echo "dataserver db not found, creating"
    flask db init
    flask db migrate -m "init"
    flask db upgrade
else
    echo "dataserver db already exists, skipping"
fi

python3 create-users.py

exec "$@"
