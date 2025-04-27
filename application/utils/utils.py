from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import ValidationError
import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify
from flask import current_app

# MARK: Error Handling
def error_response(message, status_code=400, details=None):
    response = {
        "status": "error",
        "message": message
    }
    
    if details:
        response["details"] = details
        
    return jsonify(response), status_code

def validation_error_response(err: ValidationError):
    return jsonify({"message": "Invalid input", "errors": err.messages}), 400


# MARK: Password Hashing
def hash_password(password):
    return generate_password_hash(password)

def verify_password(stored_password, provided_password):
    return check_password_hash(stored_password, provided_password) 

# MARK: Token
def encode_token(user_id, user_type):
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(days=0, hours=1),
        'iat': datetime.now(timezone.utc),
        'sub': str(user_id), # token did get created with non-string and jwt required to be string
        'role': user_type  # 'customer' or 'mechanic'
    }
    
    secret = current_app.config['SECRET_KEY']
    token = jwt.encode(payload, secret, algorithm='HS256')
    return token 

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split()[1]
            
            if not token:
                return jsonify({'message': 'missing token'}), 400
            try:
                data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
                user_id = data['sub']
            except jwt.ExpiredSignatureError as e:
                return jsonify({"message": "token expried"}), 400
            except jwt.InvalidTokenError:
                return jsonify({"message": "tinvalid token"}), 400
            
            return f(user_id, *args, **kwargs)
        
        else:
            return jsonify({'message': 'you must be logged in to access'}), 400
        
    return decorated

#MARK: Password strength validation
def is_strong_password(password):
    if len(password) < 8:
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c.isalpha() for c in password):
        return False
    return True