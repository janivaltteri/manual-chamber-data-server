#!/bin/sh

echo "starting fileserver untrypoint script"

if [ ! -f /opt/mcds/filedb/db.sqlite3 ]
then
    echo "fileserver db not found, creating"
    python3 manage.py migrate --noinput
    python3 manage.py makemigrations submit --noinput
    python3 manage.py migrate --noinput
else
    echo "fileserver db already exists, skipping"
fi

python3 manage.py shell --command="exec(open('create-users.py').read())"

exec "$@"
