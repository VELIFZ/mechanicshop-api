from flask import jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import ValidationError
import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify
from flask import current_app
from decimal import Decimal
from sqlalchemy.orm import Query
from application.models import db


# MARK: Response Formatting
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

def success_response(data=None, message="Operation successful", status_code=200, meta=None):
    """
    Standard success response format
    
    Args:
        data: The data to return to the client
        message: Success message
        status_code: HTTP status code
        meta: Additional metadata (pagination info, etc.)
        
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "status": "success",
        "message": message
    }
    
    if data is not None:
        response["data"] = data
        
    if meta is not None:
        response["meta"] = meta
        
    return jsonify(response), status_code

# MARK: Pagination
def get_pagination_params():
    """
    Extract and validate pagination parameters from request arguments
    
    Returns:
        tuple: (page, limit, sort_by, sort_order)
    """
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Ensure positive values
    page = max(1, page)
    limit = max(1, min(100, limit))  # Cap at 100 items per page
    
    return page, limit, sort_by, sort_order

def paginate_query(query, model, page, limit, sort_by='id', sort_order='asc'):
    """
    Apply pagination and sorting to a SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        model: SQLAlchemy model class
        page: Page number (starting from 1)
        limit: Number of items per page
        sort_by: Field to sort by
        sort_order: 'asc' or 'desc'
        
    Returns:
        tuple: (items, pagination_metadata)
    """
    # Sorting
    if hasattr(model, sort_by):
        if sort_order == 'desc':
            query = query.order_by(getattr(model, sort_by).desc())
        else:
            query = query.order_by(getattr(model, sort_by).asc())
            
    # Count total items for pagination metadata
    total_items = query.count()
    
    # Apply pagination
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    # Calculate pagination metadata
    total_pages = (total_items + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    # Create pagination metadata
    pagination = {
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev
    }
    
    return items, pagination

# MARK: Password Hashing
def hash_password(password):
    return generate_password_hash(password)

def verify_password(stored_password, provided_password):
    return check_password_hash(stored_password, provided_password) 

# MARK: Token
def encode_token(user_id, user_type):
    # Get token expiry from config
    token_expiry = current_app.config.get('JWT_TOKEN_EXPIRY', 3600)  # Default 1 hour if not configured
    
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(seconds=token_expiry),
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
            auth_header = request.headers['Authorization']
            
            # Check if Authorization header has the correct format
            if not auth_header.startswith('Bearer '):
                return jsonify({'message': 'Invalid authorization format. Use Bearer token'}), 401
                
            token = auth_header.split()[1]
            
            if not token:
                return jsonify({'message': 'Missing token'}), 401
            try:
                data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
                user_id = data['sub']
            except jwt.ExpiredSignatureError:
                return jsonify({"message": "Token has expired. Please log in again"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"message": "Invalid token"}), 401
            
            return f(user_id, *args, **kwargs)
        
        else:
            return jsonify({'message': 'Authorization header is required'}), 401
        
    return decorated

# MARK: Query Helpers
def apply_filters(query, model, filter_params):
    """
    Apply filters to a SQLAlchemy query based on request parameters
    
    Args:
        query: SQLAlchemy query object
        model: SQLAlchemy model class
        filter_params: Dict of {field_name: filter_value}
        
    Returns:
        SQLAlchemy query with filters applied
    """
    for field, value in filter_params.items():
        if value and hasattr(model, field):
            # String fields use LIKE for partial matching
            if isinstance(getattr(model, field).type, (db.String, db.Text)):
                query = query.filter(getattr(model, field).ilike(f"%{value}%"))
            else:
                query = query.filter(getattr(model, field) == value)
    
    return query

# MARK: Standard CRUD Operation Handlers
def handle_get_all(model, schema, filter_fields=None):
    """
    Standard handler for GET all items with pagination, filtering and sorting
    
    Args:
        model: SQLAlchemy model class
        schema: Marshmallow schema for serialization (collection schema)
        filter_fields: List of field names that can be used for filtering
        
    Returns:
        Tuple of (response, status_code)
    """
    try:
        page, limit, sort_by, sort_order = get_pagination_params()
        
        # Start with a basic query
        query = model.query
        
        # Apply filters if specified
        if filter_fields:
            filter_params = {}
            for field in filter_fields:
                value = request.args.get(field)
                if value:
                    filter_params[field] = value
            
            query = apply_filters(query, model, filter_params)
            
        # Apply pagination and get results
        items, pagination = paginate_query(query, model, page, limit, sort_by, sort_order)
        
        # Return formatted response
        return success_response(
            data=schema.dump(items),
            meta={"pagination": pagination}
        )
        
    except Exception as e:
        return error_response(str(e), 500)

#MARK: Password strength validation
def is_strong_password(password):
    if len(password) < 8:
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(c.isalpha() for c in password):
        return False
    return True

# MARK: Business Constants
TAX_RATE = 1.08  # 8% tax rate

# MARK: Cost Calculation
def calculate_ticket_cost(services, serialized_parts):
    """
    Calculate the total cost of a service ticket including tax.
    
    Args:
        services: List of Service objects with base_price attribute
        serialized_parts: List of SerializedPart objects with inventory attribute that has price
        
    Returns:
        Decimal: The calculated cost rounded to 2 decimal places
    """
    # Convert all values to Decimal to avoid float/Decimal mixed operations
    service_cost = sum(Decimal(str(service.base_price)) for service in services)
    parts_cost = sum(Decimal(str(part.inventory.price)) for part in serialized_parts)
    tax_rate = Decimal(str(TAX_RATE))
    
    total_cost = round((service_cost + parts_cost) * tax_rate, 2)
    return total_cost

