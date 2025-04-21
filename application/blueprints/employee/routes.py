from flask import request, jsonify
from . import employee_bp
from application.models import Employee, db
from application.blueprints.employee.schemas import employee_schema, employees_schema
from marshmallow import ValidationError
from application.utils import validation_error_response, hash_password, verify_password, error_response
from sqlalchemy import select

# MARK: Create Employee
@employee_bp.route('/', methods=['POST'])
def create_employee():
    try:
        employee_data = employee_schema.load(request.json)
        # Normalize email
        employee_data.email = employee_data.email.lower()
        
        # Check if email already exists
        existing_employee = db.session.query(Employee).filter_by(email=employee_data.email).first()
        if existing_employee:
            return jsonify({
                "message": "Employee already exists",
                "employee": employee_schema.dump(existing_employee)
            }), 409
        
        # Hash password if provided
        if employee_data.password:
            employee_data.password = hash_password(employee_data.password)
            
        db.session.add(employee_data)
        db.session.commit()
        return jsonify(employee_schema.dump(employee_data)), 201
    
    except ValidationError as err:
        return validation_error_response(err)
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# MARK: Get Employees
@employee_bp.route('/', methods=['GET'])
def get_employees():
    try:
        query = select(Employee)
        employees = db.session.execute(query).scalars().all()
        return jsonify(employees_schema.dump(employees))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# MARK: Get Employee by ID
@employee_bp.route('/<int:id>', methods=['GET'])
def get_employee(id):   
    try:
        query = select(Employee).where(Employee.id == id)
        employee = db.session.execute(query).scalars().first()
        
        if not employee:
            return jsonify({"error": "Employee not found"}), 404
        
        return jsonify(employee_schema.dump(employee)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# MARK: Update Employee
@employee_bp.route('/<int:id>', methods=['PUT'])
def update_employee(id):
    try:
        query = select(Employee).where(Employee.id == id)
        employee = db.session.execute(query).scalar_one_or_none()
        
        if not employee:
            return error_response("Employee not found", 404)
    
        # Load request data
        data = employee_schema.load(request.json)
        
        # Clear existing attributes and set new ones
        for key, value in request.json.items():
            if key == "password":
                setattr(employee, key, hash_password(value))
            else:
                setattr(employee, key, value)
        
        db.session.commit()
        return jsonify(employee_schema.dump(employee)), 200
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# MARK: Partial Update Employee
@employee_bp.route('/<int:id>', methods=['PATCH'])
def partial_update_employee(id):
    try:
        query = select(Employee).where(Employee.id == id)
        employee = db.session.execute(query).scalar_one_or_none()
        
        if not employee:
            return jsonify({"error": "Employee not found"}), 404
    
        # Load only provided fields
        data = request.json # work with this
        employee_schema.load(data, partial=True) #use just to validate

        # Assign updated fields manually
        for key, value in data.items():
            if key == "password":
                setattr(employee, key, hash_password(value))
            else:
                setattr(employee, key, value)

        db.session.commit()
        return jsonify(employee_schema.dump(employee)), 200
    
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# MARK: Delete Employee
@employee_bp.route('/<int:id>', methods=['DELETE'])
def delete_employee(id):
    try:
        deleted = db.session.query(Employee).filter(Employee.id == id).delete()
        
        # query.delete() returns the num of rows deleted - if 0 then no emp found 
        if deleted == 0:
            return jsonify({"error": "Employee not found"}), 404
        
        db.session.commit()
        return jsonify({"message": "Employee deleted successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500  
    
    
## do i add log actions?