# Dimep

[![Build Status](https://travis-ci.org/weverss/dimep.svg?branch=master)](https://travis-ci.org/weverss/dimep)

Usage:

```
# install
apt-get update -y
apt-get install vim git -y
git clone https://github.com/weverss/dimep.git /you-project-folder/dimep
cd /www/dimep
sudo python dimep.py

#open dimep.py on get_db_connection and change database connnection
HOST = '127.0.0.1' ;
DATABASE = 'database' ;
USER = 'user' ;
PASSWORD = 'pass' ;

# execute
python dimep.py -c NUMERO_CRACHA [-m MES] [-y ANO] [>> RELATORIO_MENSAL.TXT]
```
