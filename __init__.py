from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__, template_folder='templates')
    
app.secret_key = "%$@%^@%#^VGHGD"
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/saledb?charset=utf8mb4"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 8

db = SQLAlchemy(app)
login = LoginManager(app)
login.login_view = 'login'