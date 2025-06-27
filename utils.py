import json
import logging
from functools import wraps
from flask import jsonify, request
from flask_login import current_user

logger = logging.getLogger(__name__)

def json_response(data=None, status=200, message=""):
    """
    Create a standardized JSON response.
    
    Args:
        data: The data to include in the response
        status: HTTP status code
        message: Optional message
        
    Returns:
        tuple: (response, status_code)
    """
    response = {
        'success': 200 <= status < 300,
        'message': message,
        'data': data
    }
    return jsonify(response), status

def admin_required(f):
    """
    Decorator to ensure the user is an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return json_response(
                status=403,
                message="Admin privileges required"
            )
        return f(*args, **kwargs)
    return decorated_function

def validate_json(f):
    """
    Decorator to validate JSON request data.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return json_response(
                status=400,
                message="Request must be JSON"
            )
            
        try:
            data = request.get_json()
            return f(data, *args, **kwargs)
            
        except json.JSONDecodeError:
            return json_response(
                status=400,
                message="Invalid JSON data"
            )
    return decorated_function

def log_errors(f):
    """
    Decorator to log any exceptions that occur in the wrapped function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            raise
    return decorated_function
