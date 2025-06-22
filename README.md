# Stock Scanner Application

A Flask-based stock scanning application deployed on Render.

## Prerequisites

- Docker and Docker Compose (for local development)
- Python 3.12+ (for local development without Docker)
- Git

## Local Development with Docker (Recommended)

1. Make sure Docker and Docker Compose are installed and running
2. Clone the repository
3. Copy `.env.example` to `.env` and update the environment variables if needed
4. Run the application:
   ```bash
   docker-compose up --build
   ```
5. The application will be available at http://localhost:5000

## Local Development without Docker

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and update the environment variables
4. Run the application:
   ```bash
   python app3.py
   ```
5. The application will be available at http://localhost:5000

## Deployment

This application is configured to be deployed on Render using Docker. The deployment is automated through the `render.yaml` configuration file.

## Environment Variables

- `FLASK_APP`: The entry point of the application (default: `app3.py`)
- `FLASK_ENV`: The environment (development/production)
- `PYTHONUNBUFFERED`: Set to 1 for better logging

## Project Structure

- `app3.py`: Main application file
- `Dockerfile`: Docker configuration
- `docker-compose.yml`: Docker Compose configuration
- `requirements.txt`: Python dependencies
- `pyproject.toml`: Poetry configuration
- `render.yaml`: Render deployment configuration

## License

This project is licensed under the MIT License.
