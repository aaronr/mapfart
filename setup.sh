#!/bin/bash

# This script should be run whenever new packages are installed to ensure
# things are set for future runs, and of course to setup a new virtualenv
VENV_BASE=$(pwd)
VENV_SUBDIR='venv'
CMD=pip
REQ="requirements.txt"
EGG_CACHE="egg-cache"
APACHE_USER="www-data"
which virtualenv &>/dev/null
if [ $? -ne 0 ]; then
  echo "virtualenv command not found"
  sudo easy_install virtualenv
  exit "Install virtualenv..."
fi

if [ -d "${VENV_SUBDIR}" ]; then
  echo "virtualenv has already been created"
else
  virtualenv --no-site-packages "${VENV_SUBDIR}"
fi
source "${VENV_SUBDIR}/bin/activate"
easy_install pip

if [ -f "$REQ" ]; then
  $CMD_PREFIX $CMD install $EXTRA_ARGS -r $REQ
fi

if [ ! -d "$EGG_CACHE" ]; then
  echo "Creating the egg cache"
  mkdir -p "$EGG_CACHE"
fi
sudo chown "$APACHE_USER" "$EGG_CACHE"
echo "To switch to this venv run the command 'source $VENV_SUBDIR/bin/activate'"
