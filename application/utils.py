from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import ValidationError

# MARK: Error Handling
def error_response(message: str, status_code: int = 400):
    """Return a JSON error response with the given message and status code"""
    return jsonify({"error": message}), status_code

def validation_error_response(err: ValidationError):
    """Return a JSON response for marshmallow validation errors"""
    return jsonify({"message": "Invalid input", "errors": err.messages}), 400


# MARK: Password Hashing
def hash_password(password):
    """Hash a password using Werkzeug security"""
    return generate_password_hash(password)

def verify_password(stored_password, provided_password):
    """Verify a password against a hash"""
    return check_password_hash(stored_password, provided_password) 