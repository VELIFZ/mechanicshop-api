from flask import request, jsonify
from . import customer_bp 
from application.models import Customer, db
from .schemas import customer_schema, customers_schema
from marshmallow import ValidationError
from application.utils import validation_error_response, error_response
from sqlalchemy import select

# POST
@customer_bp.route('/', methods=['POST'])
def create_customer():
    try:
        customer_data = customer_schema.load(request.json)
        
        customer_data["email"] = customer_data["email"].lower()
        
        # Check if customer with this email already exists
        existing_customer = db.session.query(Customer).filter_by(email=customer_data['email']).first()
        
        if existing_customer:
            return jsonify({
                "message": "Customer already exists",
                "customer": customer_schema.dump(existing_customer)
            }), 409
            
        # If no existing customer, create a new one
        new_customer = Customer(**customer_data)
        db.session.add(new_customer)
        db.session.commit()
        return jsonify(customer_schema.dump(new_customer)), 201
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# GET
@customer_bp.route('/', methods=['GET'])
def get_customers():
    query = db.session.query(Customer)
    customers = db.session.execute(query).scalars().all()
    return jsonify(customers_schema.dump(customers))

@customer_bp.route('/<int:customer_id>', methods=['GET'])
def get_customer(customer_id):
    customer = db.session.query(Customer).get(customer_id)
    if customer is None:
        return error_response("Customer not found", 404)
    return jsonify(customer_schema.dump(customer)), 200

# PUT
@customer_bp.route('/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    query = select(Customer).where(Customer.id == customer_id)
    customer = db.session.execute(query).scalars().first()
    
    if customer is None:
        return error_response("Customer not found", 404)
    
    try:
        customer_data = customer_schema.load(request.json)
        customer_data["email"] = customer_data["email"].lower()
        
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
def patch_customer(customer_id): 
    try:
        customer = db.session.get(Customer, customer_id)
        
        if customer is None:
            return error_response("Customer not found", 404)
        
        customer_data = customer_schema.load(request.json, partial=True) 
        
        if "email" in customer_data:
            customer_data["email"] = customer_data["email"].lower()
   
        
        for key, value in customer_data.items():
            setattr(customer, key, value)
            
        db.session.commit()
        return jsonify(customer_schema.dump(customer)), 200  
    
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500) 
    
# DELETE
@customer_bp.route('/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    query = select(Customer).where(Customer.id == customer_id)
    customer = db.session.execute(query).scalars().first()
    if customer is None:
        return jsonify({"error": "Customer not found"}), 404
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": f"{customer.id} deleted successfully"}), 204 # 204 no content
