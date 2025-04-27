from flask import request, jsonify
from . import customer_bp 
from application.models import Customer, ServiceTicket, db
from .schemas import customer_schema, customers_schema, login_schema
from application.extensions import limiter, cache
from marshmallow import ValidationError
from application.utils.utils import validation_error_response, error_response, encode_token, token_required, verify_password, hash_password, is_strong_password
from sqlalchemy import select

#POST/login
@customer_bp.route("/login", methods=['POST'])
@limiter.limit('3 per 10 minutes')
def login():
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
        
        response = {
            'status': 'success',
            'message': 'successfully logged in.',
            'token': token
        }
        
        return jsonify(response), 200
    else:
        return error_response("Invalid email or password", 401)

# POST/create new
@customer_bp.route('/', methods=['POST'])
@limiter.limit("3 per hour")
def create_customer():
    try:
        customer_data = customer_schema.load(request.json)
        customer_data["email"] = customer_data["email"].lower().strip()
        
        # Check password strength
        if not is_strong_password(customer_data['password']):
            return error_response("Password must be at least 8 characters, including letters and numbers.", 400)
        
        # Check if customer with this email already exists
        existing_customer = db.session.query(Customer).filter_by(email=customer_data['email']).first()
        if existing_customer:
            return error_response("Customer already exists", 409, {"customer": customer_schema.dump(existing_customer)})
            
        # If no existing customer, create a new one
        if 'password' in customer_data:
            customer_data['password'] = hash_password(customer_data['password'])
            
        new_customer = Customer(**customer_data)
        db.session.add(new_customer)
        db.session.commit()
        return jsonify(customer_schema.dump(new_customer)), 201
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        print(f"DB ERROR: {e}")
        db.session.rollback()
        return error_response(str(e), 500)
    

# GET 
# get curtomer with Pagination, Filter, and Sort
@customer_bp.route('/', methods=['GET'])
@cache.cached(timeout=60)
def get_customers():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        name_filter = request.args.get('name')
        email_filter = request.args.get('email')
        sort_by = request.args.get('sort_by', 'id')  # default sort by id
        sort_order = request.args.get('sort_order', 'asc')  # asc or desc
        
        query = db.session.query(Customer)
        
        # Filtering
        if name_filter:
            query = query.filter(Customer.name.ilike(f"%{name_filter}%"))
        if email_filter:
            query = query.filter(Customer.email.ilike(f"%{email_filter}%"))
            
        # Sorting
        if sort_order == 'desc':
            query = query.order_by(getattr(Customer, sort_by).desc())
        else:
            query = query.order_by(getattr(Customer, sort_by).asc())

        # Pagination
        customers = query.offset((page - 1) * limit).limit(limit).all()

        return jsonify(customers_schema.dump(customers)), 200

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
#  Get  by ID
@customer_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_customer(customer_id, id):   
    try:
        query = select(Customer).where(Customer.id == id)
        customer = db.session.execute(query).scalars().first()
        
        if not customer:
            return error_response("Customer not found", 404)
        
        return jsonify(customer_schema.dump(customer)), 200
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# /me -get profile
@customer_bp.route('/me', methods=['GET'])
@limiter.limit("10 per minute")
@token_required
def get_my_profile(customer_id):
    customer = db.session.get(Customer, customer_id)
    if customer is None:
        return error_response("Customer not found", 404)
    return jsonify(customer_schema.dump(customer)), 200


# my tickets with pagination
@customer_bp.route('/me/tickets', methods=['GET'])
@token_required
def get_my_tickets(customer_id):
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 5, type=int)
        status = request.args.get('status', None)

        query = db.session.query(ServiceTicket).filter(ServiceTicket.customer_id == customer_id)
        if status:
            query = query.filter_by(status=status)
            
        tickets = query.offset((page - 1) * limit).limit(limit).all()
        
        # Imported here to avoid circular import!
        from application.blueprints.service_ticket.schemas import service_tickets_schema
        return jsonify(service_tickets_schema.dump(tickets)), 200

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    

# PUT
@customer_bp.route('/<int:customer_id>', methods=['PUT'])
@limiter.limit('20 per hour')
@token_required
def update_customer(current_customer_id, customer_id):
    query = select(Customer).where(Customer.id == customer_id)
    customer = db.session.execute(query).scalars().first()
    
    if customer is None:
        return error_response("Customer not found", 404)
    
    try:
        customer_data = customer_schema.load(request.json)
        customer_data["email"] = customer_data["email"].lower().strip()
        
        existing = db.session.query(Customer).filter(Customer.email == customer_data["email"], Customer.id != customer_id).first()
        if existing:
            return error_response("Email already taken", 400)
        
        for key, value in customer_data.items():
            setattr(customer, key, value)
            
        db.session.commit()
        return jsonify(customer_schema.dump(customer))
    
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
# PATCH
@customer_bp.route('/<int:customer_id>', methods=['PATCH'])
@limiter.limit('20 per hour')
@token_required
def patch_customer(current_customer_id, customer_id): 
    try:
        customer = db.session.get(Customer, customer_id)
        
        if customer is None:
            return error_response("Customer not found", 404)
        
        customer_data = customer_schema.load(request.json, partial=True) 
        
        if "email" in customer_data:
            customer_data["email"] = customer_data["email"].lower().strip()
   
        
        for key, value in customer_data.items():
            setattr(customer, key, value)
            
        db.session.commit()
        return jsonify(customer_schema.dump(customer)), 200  
    
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500) 
    
# PATCH /update-password
@customer_bp.route('/update-password', methods=['PATCH'])
@token_required
def update_password(customer_id):
    try:
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return error_response("Old and new passwords are required.", 400)

        if not is_strong_password(new_password):
            return error_response("Password must be at least 8 characters, including letters and numbers.", 400)

        customer = db.session.get(Customer, customer_id)
        if customer is None:
            return error_response("Customer not found.", 404)

        if not verify_password(customer.password, old_password):
            return error_response("Old password is incorrect.", 401)

        customer.password = hash_password(new_password)
        db.session.commit()

        return jsonify({"message": "Password updated successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
    
# DELETE- toekn base
@customer_bp.route('/', methods=['DELETE']) # after adding token took out <int:customer_id>
@limiter.limit('5 per hour')
@token_required
def delete_customer(customer_id):
    try:
        query = select(Customer).where(Customer.id == customer_id)
        customer = db.session.execute(query).scalars().first()
        
        if customer is None:
            return error_response("Customer not found", 404)
        
        if customer.tickets:
            return error_response("Cannot delete customer with active service tickets.", 400)
        
        db.session.delete(customer)
        db.session.commit()
        
        # Note: For 204 responses, don't return a body as per HTTP standard
        return "", 204
    except Exception as e:
        print("ROUTE ERROR:", str(e))
        db.session.rollback()
        return error_response(str(e), 400)
