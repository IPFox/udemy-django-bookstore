#!/bin/bash

# Prepare configuration file for use in Heroku
CONFIG="bookstore/secrets.json"
cp bookstore/secrets.json.template $CONFIG

# Run migration to handle the DB errors at Heroku
python manage.py migrate store