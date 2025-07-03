#!/bin/bash

export FLASK_APP=main.py
export FLASK_ENV=development
export PYTHONPATH="$(pwd)"

flask run --host=localhost.localdomain --port=5000 \
  --cert=localhost.localdomain.crt \
  --key=localhost.localdomain.key
