import os
from app import create_app

# Create the Flask app using the factory function
app = create_app()

if __name__ == "__main__":
    # Get the port number from environment variables or default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    # Run the Flask app on all IPs (0.0.0.0) to make it accessible externally, with the specified port
    app.run(host="0.0.0.0", port=port, debug=True)
