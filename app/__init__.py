import os
from flask import Flask
from dotenv import load_dotenv

# Load .env variables if running locally (not needed on Render but doesn't hurt)
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "change_me!")

# --- Enable CORS ONLY for your Webflow frontend! ---
from flask_cors import CORS
CORS(app, origins=["https://fitfound.webflow.io"], supports_credentials=True)
# If you ever need to allow local testing: origins=["https://fitfound.webflow.io", "http://localhost:3000"]

from app import routes  # Import your main routes.py (must be after app is created)
