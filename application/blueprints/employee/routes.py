from flask import request, jsonify
from . import employee_bp
from application.models import Employee, ServiceTicket, employee_service_ticket, db
from application.blueprints.employee.schemas import employee_schema, employees_schema, login_schema
from marshmallow import ValidationError
from application.utils.utils import validation_error_response, hash_password, verify_password, error_response, encode_token, token_required, is_strong_password
from sqlalchemy import select
from application.extensions import limiter, cache

# MARK: POST-Login
@employee_bp.route('/login', methods=['POST'])
@limiter.limit("3 per minute")
def login():
    try:
        credentials = login_schema.load(request.get_json())
        # Access attributes of the employee object instead of dictionary keys -
        email = credentials.email
        password = credentials.password
    except ValidationError as e:
        return validation_error_response(e)
    
    query = select(Employee).where(Employee.email == email)
    employee = db.session.execute(query).scalars().first()
    
    if employee and verify_password(employee.password, password):
        token = encode_token(employee.id, 'employee')
        
        response = {
            'status': 'success',
            'message': 'successfully logged in.',
            'token': token
        }
        
        return jsonify(response), 200
    else:
        return error_response("Invalid email or password", 401)

# MARK: POST -Create Employee
@employee_bp.route('/', methods=['POST'])
@limiter.limit("3 per hour")
def create_employee():
    try:
        employee_data = employee_schema.load(request.json)
        # Normalize email
        employee_data.email = employee_data.email.lower()
        
        if not is_strong_password(employee_data.password):
            return error_response("Password must be at least 8 characters, including letters and numbers.", 400)
        
        # Check if email already exists
        existing_employee = db.session.query(Employee).filter_by(email=employee_data.email).first()
        if existing_employee:
            return error_response("Employee already exists", 409, {"employee": employee_schema.dump(existing_employee)})
        
        if employee_data.password:
            employee_data.password = hash_password(employee_data.password)
            
        db.session.add(employee_data)
        db.session.commit()
        return jsonify(employee_schema.dump(employee_data)), 201
    
    except ValidationError as err:
        return validation_error_response(err)
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# MARK: Get Employees
@employee_bp.route('/', methods=['GET'])
@token_required
@cache.cached(timeout=60)
def get_employees(employee_id):
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        name_filter = request.args.get('name')
        email_filter = request.args.get('email')
        sort_by = request.args.get('sort_by', 'id')  
        sort_order = request.args.get('sort_order', 'asc')
        role_filter = request.args.get('role')
        
        query = select(Employee)
        
        if name_filter:
            query = query.filter(Employee.name.ilike(f"%{name_filter}%"))
        if email_filter:
            query = query.filter(Employee.email.ilike(f"%{email_filter}%")) 
        if role_filter:
            query = query.filter(Employee.role.ilike(f"%{role_filter}%"))
        if sort_order == 'desc':
            query = query.order_by(getattr(Employee, sort_by).desc())
        else:
            query = query.order_by(getattr(Employee, sort_by).asc())
        
        
        employees = db.session.execute(query).scalars().all()
        return jsonify(employees_schema.dump(employees))
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# MARK: Get Employee by ID
@employee_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_employee(employee_id, id):   
    try:
        query = select(Employee).where(Employee.id == id)
        employee = db.session.execute(query).scalars().first()
        
        if not employee:
            return error_response("Employee not found", 404)
        
        return jsonify(employee_schema.dump(employee)), 200
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
# MARK: Get Profile
@employee_bp.route('/me', methods=['GET'])
@limiter.limit("10 per minute")
@token_required
def get_my_profile(employee_id):
    employee = db.session.get(Employee, employee_id)
    if employee is None:
        return error_response("Employee not found", 404)
    return jsonify(employee_schema.dump(employee)), 200

# MARK: GET  -Get employee's assigned tickets
@employee_bp.route('/me/tickets', methods=['GET'])
@token_required
@limiter.limit("10 per minute")
def get_my_tickets(employee_id):
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 5, type=int)

        employee = db.session.get(Employee, employee_id)
        if not employee:
            return error_response("Employee not found", 404)

        tickets = employee.tickets  
        
        start = (page - 1) * limit
        end = start + limit
        paginated_tickets = tickets[start:end]

        # Imported here to avoid circular import!
        from application.blueprints.service_ticket.schemas import service_tickets_schema
        return jsonify(service_tickets_schema.dump(paginated_tickets)), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# MARK: GET - Get mechanics by ticket count
@employee_bp.route('/by-ticket-count', methods=['GET'])
def get_mechanics_by_ticket_count():
    try:
        ticket_count_label = db.func.count(ServiceTicket.id).label('ticket_count')
        
        # More explicit query with select_from
        query = db.select(Employee, ticket_count_label
        ).select_from(Employee
        ).join(employee_service_ticket, Employee.id == employee_service_ticket.c.mechanic_id
        ).join(ServiceTicket, ServiceTicket.id == employee_service_ticket.c.service_ticket_id
        ).group_by(Employee.id
        ).order_by(ticket_count_label.desc()
        )
        
        mechanics = db.session.execute(query).all()
        
        result = [{"id": m[0].id, "name": m[0].name, "ticket_count": m[1]} for m in mechanics]
        return jsonify(result), 200
    
    except Exception as e:
        import traceback
        print(f"Error->> in get_mechanics_by_ticket_count: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return error_response(str(e), 500)

# MARK: PUT -Update Employee
@employee_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_employee(employee_id, id):
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
        return error_response(str(e), 500)

# MARK: Partial Update Employee
@employee_bp.route('/<int:id>', methods=['PATCH'])
@token_required
def partial_update_employee(employee_id, id):
    try:
        query = select(Employee).where(Employee.id == id)
        employee = db.session.execute(query).scalar_one_or_none()
        
        if not employee:
            return error_response("Employee not found", 404)
    
        # Load only provided fields
        data = request.json 
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
        return error_response(str(e), 500)

# MARK: Delete Employee
@employee_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@limiter.limit("5 per hour")
def delete_employee(employee_id, id):
    try:
        deleted = db.session.query(Employee).filter(Employee.id == id).delete()
        
        # query.delete() returns the num of rows deleted - if 0 then no emp found 
        if deleted == 0:
            return error_response("Employee not found", 404)
        
        db.session.commit()
        return jsonify({"message": "Employee deleted successfully"}), 200
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)  