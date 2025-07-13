import os
from flask import Flask
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "change_me!")

    # --- Enable CORS for your frontend ---
    from flask_cors import CORS
    CORS(app, origins=["https://fitfound.webflow.io"], supports_credentials=True)

    # --- Register main app routes (non-AI endpoints, like jobs, signup, login) ---
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # --- Register AI blueprints ---
    from .ai_profile import ai_profile_bp
    from .ai_culture import ai_culture_bp
    from .ai_compensation import ai_compensation_bp

    app.register_blueprint(ai_profile_bp)
    app.register_blueprint(ai_culture_bp)
    app.register_blueprint(ai_compensation_bp)

    return app
