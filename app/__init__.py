from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)

from app.routes import auth, match, geo, sheets
app.register_blueprint(auth.bp)
app.register_blueprint(match.bp)
app.register_blueprint(geo.bp)
app.register_blueprint(sheets.bp)
