import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env if running locally

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "change_me!")

# Enable CORS for Webflow site
from flask_cors import CORS
CORS(app, origins=["https://fitfound.webflow.io"])

from app import routes  # this should import your main routes.py
