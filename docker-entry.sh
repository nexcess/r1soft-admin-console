#!/bin/sh

DB_FILE="$(echo 'print SQLITE_DB_FILE' | python -i $RAC_SETTINGS 2>/dev/null)"
[ ! -f "$DB_FILE" ] && python rac-cmd.py create_db

case "$1" in
    runserver|run_server)
        gunicorn -b '0.0.0.0:5000' -w 4 -t 300 rac:app
        ;;
    *)
        python rac-cmd.py "$@"
        ;;
esac
