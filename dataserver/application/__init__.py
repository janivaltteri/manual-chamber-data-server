from flask import Flask
from config import configuration, logging_dir
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

import logging

server = Flask(__name__)
server.config.from_object(configuration)

logging.basicConfig(filename=logging_dir + "datalog.txt",
                    level=logging.DEBUG,
                    format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

db = SQLAlchemy(server)
migrate = Migrate(server,db)
login = LoginManager(server)
login.login_view = 'login'

from application import routes, models
