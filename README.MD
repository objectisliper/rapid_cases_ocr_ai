##LOCAL SETUP
- If new system

```
sudo apt install python3-dev &&
sudo apt install python3-venv &&
sudo apt install tesseract-ocr &&
sudo apt install libtesseract-dev &&
sudo apt-get install libmysqlclient-dev &&
sudo apt install ffmpeg
```
- Set up mysql
https://www.digitalocean.com/community/tutorials/mysql-ubuntu-18-04-ru

- in project base directory
```
cp service/conqueror/settings/local.py.example service/conqueror/settings/local.py && 
cp service/conqueror/settings/database.yaml.example service/conqueror/settings/database.yaml
```
- Change settings to your DB creds in service/conqueror/settings/database.yaml.example

- Create venv

```
python3 -m venv venv
```

- Install all libs

```
source venv/bin/activate && 
pip install --upgrade pip && 
pip install -r requirements.txt && 
```

- ATTENTION! If you have data in your sql schema, don't init it!
- If you have clear schema & wanna to init tables (for local use only), 
use next command:
```
python db_init.py
```

- After db has been connected, start application

```
python app.py
```

- For local scheduling test, you need to install rabbitmq
```
sudo apt-get install -y erlang
sudo apt-get install rabbitmq-server
```

- Then start and test rabbitMQ

```
systemctl enable rabbitmq-server
systemctl start rabbitmq-server
systemctl status rabbitmq-server
```

- For windows use it https://www.rabbitmq.com/install-windows.html

- For visual management on localhost:15672 of queues enable special plugin:

```
rabbitmq-plugins enable rabbitmq_management
```

Default credentials to admin is login - guest , and password - guest

- On local machine or for test you can use terminal workers and beats, like this:

```
celery -A service.conqueror.scheduling worker -l info
```

##VPS SETUP

First make sure, that on vps already installed python:

```
sudo apt install python3-dev &&
sudo apt-get install mysql-server &&
sudo apt-get install libmysqlclient-dev
```

##DEPLOY

Don't forget to setup configs in deploy_tools/deploy_local.yaml, start from copying example:

```
cp deploy_tools/deploy_local.yaml.example deploy_tools/deploy_local.yaml
```

After all needed services was installed, and python virtual environment
setup, just type
```
sudo su
```
```
. venv/bin/activate &&
fab -f deploy_tools/fabfile.py deploy
```
from root directory.

##TESTS

Start all from virtual environment

```
. venv/bin/activate
```

###Integration tests
```
python -m unittest discover -s service.conqueror.tests.integration -p '*_test.py'
```

###Unit tests
```
python -m unittest discover -s service.conqueror.tests.unit -p '*_test.py'
```