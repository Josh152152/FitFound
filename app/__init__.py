import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

def create_app():
    # Initialize the Flask application
    app = Flask(__name__)

    # Load the secret key from environment variables
    app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "change_me!")

    # Enable Cross-Origin Resource Sharing (CORS) to allow your Webflow frontend
    from flask_cors import CORS
    CORS(app, origins=["https://fitfound.webflow.io"], supports_credentials=True)

    # Register non-AI routes for your app (such as jobs, signup, login)
    from .routes import main_bp
    app.register_blueprint(main_bp)

    # Register AI-related blueprints that manage specific AI sections
    from .ai_profile import ai_profile_bp
    from .ai_culture import ai_culture_bp
    from .ai_compensation import ai_compensation_bp

    app.register_blueprint(ai_profile_bp)
    app.register_blueprint(ai_culture_bp)
    app.register_blueprint(ai_compensation_bp)

    return app
