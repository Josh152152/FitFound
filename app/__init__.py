import os
from flask import Flask
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables from the .env file
load_dotenv()

def create_app():
    # Initialize the Flask application
    app = Flask(__name__)

    # Load the secret key from environment variables
    app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY", "change_me!")

    # Enable Cross-Origin Resource Sharing (CORS) to allow your Webflow frontend
    CORS(app, origins=["https://fitfound.webflow.io"], supports_credentials=True)

    # Register the main blueprint for general routes (non-AI)
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Register AI-related blueprints that manage specific AI sections
    from .ai_profile import bp as ai_profile_bp
    from .ai_culture import bp as ai_culture_bp
    from .ai_compensation import bp as ai_compensation_bp

    # Register all blueprints
    app.register_blueprint(ai_profile_bp, url_prefix='/ai/profile')
    app.register_blueprint(ai_culture_bp, url_prefix='/ai/culture')
    app.register_blueprint(ai_compensation_bp, url_prefix='/ai/compensation')

    return app
