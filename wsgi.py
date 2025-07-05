from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Ensure the secret key is set
    if not app.config['SECRET_KEY']:
        raise ValueError("No SECRET_KEY set for Flask application")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
