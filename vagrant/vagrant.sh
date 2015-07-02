#!/bin/sh

sudo su

# deps
apt-get update -y
apt-get install vim git python-dev freetds-dev python-pip -y
pip install pymssql
pip install tabulate

# optional
git clone https://github.com/Webysther/dimep.git /www/dimep
cd /www/dimep
python dimep.py