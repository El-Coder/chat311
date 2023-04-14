#!/usr/bin/env bash
source $(cd /opt/contribot/ && poetry env info -p)/bin/activate
exec "$@"
