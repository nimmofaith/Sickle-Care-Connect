"""
JWT Token Utilities for Authentication
Handles token generation and verification for Admin, Doctor, and Patient roles
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

# Get secret key from environment or use default (IMPORTANT: Change in production)
JWT_SECRET_KEY = os.getenv(
    'JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def generate_token(user_id, user_type, email):
    """
    Generate a JWT token for a user

    Args:
        user_id: Database ID of the user
        user_type: Type of user ('admin', 'doctor', 'patient')
        email: User's email address

    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'user_type': user_type,
        'email': email,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token):
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string to verify

    Returns:
        Tuple of (payload_dict, error_message)
        If valid: (payload, None)
        If invalid: (None, error_message)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print(
            f"DEBUG: Token verified successfully for user: {payload.get('user_id')}")
        return payload, None
    except jwt.ExpiredSignatureError:
        print(f"DEBUG: Token has expired")
        return None, "Token has expired"
    except jwt.InvalidTokenError as e:
        print(f"DEBUG: Invalid token error: {str(e)}")
        return None, "Invalid token"
    except Exception as e:
        print(f"DEBUG: Token verification failed: {str(e)}")
        return None, f"Token verification failed: {str(e)}"


def extract_token_from_header():
    """
    Extract JWT token from Authorization header

    Returns:
        Token string or None if not found
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None

    return auth_header.split(' ', 1)[1]


def require_auth(user_type=None):
    """
    Decorator to require JWT authentication for a route

    Args:
        user_type: Optional - check for specific user type ('admin', 'doctor', 'patient')

    Returns:
        Decorated function that checks JWT before execution
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == 'OPTIONS':
                return jsonify({}), 200  # Allow preflight CORS requests

            token = extract_token_from_header()
            if not token:
                return jsonify({"message": "Authorization header required"}), 401

            payload, error = verify_token(token)
            if error:
                return jsonify({"message": error}), 401

            # Check user type if specified
            if user_type and payload.get('user_type') != user_type:
                return jsonify({"message": f"This endpoint requires {user_type} privileges"}), 403

            # Pass the payload to the route handler
            return f(user_data=payload, *args, **kwargs)

        return decorated_function

    return decorator
