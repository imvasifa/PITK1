"""
Custom error handlers for the application.
"""
import logging
from flask import render_template, jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register error handlers with the Flask application."""
    # Handle 404 errors
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 Not Found: {request.url}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found.',
                'status': 404
            }), 404
        return render_template('errors/404.html'), 404
    
    # Handle 403 errors
    @app.errorhandler(403)
    def forbidden_error(error):
        logger.warning(f"403 Forbidden: {request.url}")
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource.',
                'status': 403
            }), 403
        return render_template('errors/403.html'), 403
    
    # Handle 500 errors
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 Internal Server Error: {error}", exc_info=True)
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Please try again later.',
                'status': 500
            }), 500
        return render_template('errors/500.html'), 500
    
    # Handle database errors
    @app.errorhandler(Exception)
    def handle_exception(error):
        # Pass through HTTP errors
        if isinstance(error, HTTPException):
            return error
        
        # Log the error
        logger.error(f"Unhandled Exception: {error}", exc_info=True)
        
        # Handle API requests
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Please try again later.',
                'status': 500
            }), 500
            
        # Handle regular requests
        return render_template('errors/500.html'), 500
