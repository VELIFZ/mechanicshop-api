from flask import request, jsonify
from . import customer_bp 
from application.models import Customer, ServiceTicket, db
from .schemas import customer_schema, login_schema
from application.extensions import limiter
from marshmallow import ValidationError
from application.utils.utils import (
    validation_error_response, error_response, encode_token, token_required, 
    verify_password, hash_password, is_strong_password, success_response,
    get_pagination_params, paginate_query
)
from sqlalchemy import select

#MARK: POST
# ---login---
@customer_bp.route("/login", methods=['POST'])
@limiter.limit('3 per 10 minutes')
def login():
    if not request.is_json:
        return error_response("Invalid or missing JSON body", 400)
        
    try:
        credentials = login_schema.load(request.json)
        email = credentials['email'].lower().strip()
        password = credentials['password']
    except ValidationError as e:
        return validation_error_response(e)
    
    query = select(Customer).where(Customer.email == email)
    customer = db.session.execute(query).scalars().first()
    
    if customer and verify_password(customer.password, password):
        token = encode_token(customer.id, 'customer')
        
        return success_response(
            message="Successfully logged in",
            data={"token": token}
        )
    else:
        return error_response("Invalid email or password", 401)

# ---Create new---
@customer_bp.route('/', methods=['POST'])
@limiter.limit("3 per hour")
def create_customer():
    if not request.is_json:
        return error_response("Invalid or missing JSON body", 400)
        
    try:
        customer_data = customer_schema.load(request.json)
        
        # Check duplicate email
        existing_customer = db.session.query(Customer).filter_by(email=customer_data['email']).first()
        if existing_customer:
            return error_response("Customer already exists", 409, {"customer": customer_schema.dump(existing_customer)})
            
        # If no existing customer, create a new one
        if 'password' in customer_data:
            customer_data['password'] = hash_password(customer_data['password'])
            
        new_customer = Customer(**customer_data)
        db.session.add(new_customer)
        db.session.commit()
        
        return success_response(message="Customer created successfully", data=customer_schema.dump(new_customer), status_code=201)
    
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

#MARK: GET
# --- profile /me---
@customer_bp.route('/me', methods=['GET'])
@limiter.limit("10 per minute")
@token_required(expected_role="customer")
def get_my_profile(user_id):
    customer = db.session.get(Customer, user_id)
    if customer is None:
        return error_response("Customer not found", 404)
    return success_response(data=customer_schema.dump(customer))


# ---my tickets with pagination---
@customer_bp.route('/me/tickets', methods=['GET'])
@token_required(expected_role="customer")
def get_my_tickets(user_id):
    try:
        page, limit, sort_by, sort_order = get_pagination_params()
        
        # Base query filtered by customer_id
        query = db.session.query(ServiceTicket).filter(ServiceTicket.customer_id == user_id)
        
        # Additional status filter if provided
        status = request.args.get('status')
        if status:
            # Verify status is a valid value before filtering
            valid_statuses = ['open', 'in_progress', 'closed']
            if status in valid_statuses:
                query = query.filter_by(status=status)
            else:
                return error_response(f"Invalid status value. Must be one of: {', '.join(valid_statuses)}", 400)
            
        # Apply pagination
        tickets, pagination = paginate_query(query, ServiceTicket, page, limit, sort_by, sort_order)
        
        # Imported here to avoid circular import!
        from application.blueprints.service_ticket.schemas import service_tickets_schema
        return success_response(
            data=service_tickets_schema.dump(tickets),
            meta={"pagination": pagination}
        )

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
#MARK: PATCH
# allow only basic customer info changes
@customer_bp.route('/<int:customer_id>', methods=['PATCH'])
@limiter.limit('20 per hour')
@token_required(expected_role="customer")
def patch_customer(user_id, customer_id): 
    if not request.is_json:
        return error_response("Invalid or missing JSON body", 400)
        
    try:
        if int(user_id) != customer_id:
            return error_response("Unauthorized to update this profile", 403)
        
        customer = db.session.get(Customer, customer_id) 
        if customer is None:
            return error_response("Customer not found", 404)
        
        data = request.json
        allow_changes = {"name", "email", "phone"}
        for key in data:
            if key not in allow_changes:
                return error_response(f"Field '{key}' cannot be updated by customer.", 403)
            
        customer_data = customer_schema.load(request.json, partial=True)
          
        for key, value in customer_data.items():
            if key == 'email':
                existing = db.session.query(Customer).filter(Customer.email == value, Customer.id != customer_id).first()
                if existing:
                    return error_response("Email already taken", 400)
            setattr(customer, key, value)
            
        db.session.commit()
        return success_response(data=customer_schema.dump(customer))
    
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# update password
@customer_bp.route('/me/update-password', methods=['PATCH'])
@token_required(expected_role="customer")
def update_password(user_id):
    if not request.is_json:
        return error_response("Invalid or missing JSON body", 400)
        
    try:
        data = request.get_json()
        
        if not data or 'current_password' not in data or 'new_password' not in data:
            return error_response("Missing required fields", 400)
        
        customer = db.session.get(Customer, user_id)
        if not customer:
            return error_response("Customer not found", 404)
        
        # Verify current password
        if not verify_password(customer.password, data['current_password']):
            return error_response("Current password is incorrect", 401)
        
        # Check password strength
        if not is_strong_password(data['new_password']):
            return error_response("Password must be at least 8 characters, including letters and numbers.", 400)
        
        # Update password
        customer.password = hash_password(data['new_password'])
        db.session.commit()
        
        return success_response(message="Password updated successfully")
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    