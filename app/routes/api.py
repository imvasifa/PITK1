from flask import Blueprint, jsonify, current_app
from flask_login import current_user
from datetime import datetime, timedelta
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_bp.route('/check-licence', methods=['GET'])
def check_licence():
    try:
        # For now, return a basic response
        # In a real app, you'd check the actual license status here
        license_data = {
            'hasLicence': True,
            'isExpired': False,
            'expiresAt': (datetime.utcnow() + timedelta(days=30)).isoformat(),
            'expiresAtIST': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S %Z')
        }
        return jsonify(license_data)
    except Exception as e:
        logger.error(f"Error checking license: {str(e)}")
        return jsonify({
            'hasLicence': False,
            'isExpired': True,
            'error': 'Error checking license status'
        }), 500
