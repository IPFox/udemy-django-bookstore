release: scripts/heroku_deploy.sh
web: cp bookstore/secrets.json.template bookstore/secrets.json && cd bookstore && gunicorn bookstore.wsgi --log-file -