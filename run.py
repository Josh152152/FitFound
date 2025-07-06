import os
from app import app
from flask_cors import CORS

# Enable CORS on your Flask app
CORS(app)

if __name__ == "__main__":
    # Render provides the PORT env variable; fallback to 5000 for local dev
    port = int(os.environ.get("PORT", 5000))
    # Listen on all interfaces so Render can reach your app
    app.run(host="0.0.0.0", port=port, debug=True)
