#!/bin/bash

# Exit code starts at 0 but is modified if any checks fail
EXIT=0

# Output a line prefixed with a timestamp
info()
{
	echo "$(date +'%F %T') |"
}

# Track number of seconds required to run script
START=$(date +%s)
echo "$(info) starting build checks."

# Syntax check all python source files
SYNTAX=$(find . -name "*.py" -type f -exec python -m py_compile {} \; 2>&1)
if [[ ! -z $SYNTAX ]]; then
	echo -e "$SYNTAX"
	echo -e "\n$(info) detected one or more syntax errors, failing build."
	EXIT=1
fi

# Check all python source files for PEP 8 compliance, but explicitly
# ignore:
#  - E501: line greater than 80 characters in length
# pep8 --ignore=E501 netbox/
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more PEP 8 errors detected, failing build."
	EXIT=$RC
fi

# Prepare configuration file for use in CI
CONFIG="bookstore/secrets.json"
cp bookstore/secrets.json.template $CONFIG
sed -i -e "s/ALLOWED_HOSTS = \[\]/ALLOWED_HOSTS = \['*'\]/g" $CONFIG

# Run NetBox tests
./bookstore/manage.py test store/
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "\n$(info) one or more tests failed, failing build."
	EXIT=$RC
fi

# Show build duration
END=$(date +%s)
echo "$(info) exiting with code $EXIT after $(($END - $START)) seconds."

exit $EXIT
