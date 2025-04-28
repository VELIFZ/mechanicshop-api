from flask import request, jsonify
from . import employee_bp
from application.models import Employee, ServiceTicket, employee_service_ticket, db
from application.blueprints.employee.schemas import employee_schema, employees_schema, login_schema
from marshmallow import ValidationError
from application.utils.utils import (
    validation_error_response, hash_password, verify_password, error_response, 
    encode_token, token_required, is_strong_password, success_response,
    get_pagination_params, paginate_query, apply_filters
)
from sqlalchemy import select
from application.extensions import limiter, cache
from sqlalchemy import func

# MARK: POST
#---login----
@employee_bp.route('/login', methods=['POST'])
@limiter.limit("3 per minute")
def login():
    try:
        credentials = login_schema.load(request.get_json())
        employee = db.session.query(Employee).filter_by(email=credentials.email.lower()).first()

        if employee and verify_password(employee.password, credentials.password):
            token = encode_token(employee.id, 'employee')
            return success_response(message="Successfully logged in", data={"token": token})

        return error_response("Invalid email or password", 401)

    except ValidationError as e:
        return validation_error_response(e)

#---Create Employee----
@employee_bp.route('/', methods=['POST'])
@limiter.limit("3 per hour")
def create_employee():
    try:
        employee_data = employee_schema.load(request.json)
        employee_data.email = employee_data.email.lower()
        
        if not is_strong_password(employee_data.password):
            return error_response("Password must be at least 8 characters, including letters and numbers.", 400)
        
        existing_employee = db.session.query(Employee).filter_by(email=employee_data.email).first()
        if existing_employee:
            return error_response("Employee already exists", 409, {"employee": employee_schema.dump(existing_employee)})
        
        if employee_data.password:
            employee_data.password = hash_password(employee_data.password)
            
        db.session.add(employee_data)
        db.session.commit()
        return success_response(message="Employee created successfully", data=employee_schema.dump(employee_data), status_code=201)
    
    except ValidationError as err:
        return validation_error_response(err)

# MARK: GET
# ------GET All Employees------
@employee_bp.route('/', methods=['GET'])
@token_required
@cache.cached(timeout=60)
def get_employees(user_id):
    page, limit, sort_by, sort_order = get_pagination_params()
    query = db.session.query(Employee)
    filter_params = {key: request.args.get(key) for key in ('name', 'email', 'role')}
    query = apply_filters(query, Employee, filter_params)
    employees, pagination = paginate_query(query, Employee, page, limit, sort_by, sort_order)
    
    return success_response(data=employees_schema.dump(employees), meta={"pagination": pagination})

# ---- Get by ID ----
@employee_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_employee(user_id, id):   
    employee = db.session.get(Employee, id)
    if not employee:
        return error_response("Employee not found", 404)
    return success_response(data=employee_schema.dump(employee))
    
# ---- Profile ------
@employee_bp.route('/me', methods=['GET'])
@limiter.limit("10 per minute")
@token_required
def get_my_profile(user_id):
    employee = db.session.get(Employee, user_id)
    if employee is None:
        return error_response("Employee not found", 404)
    return success_response(data=employee_schema.dump(employee))

# ---- employee's assigned tickets----
@employee_bp.route('/me/tickets', methods=['GET'])
@token_required
@limiter.limit("10 per minute")
def get_my_tickets(user_id):
    employee = db.session.get(Employee, user_id)
    if not employee:
        return error_response("Employee not found", 404)

    page, limit = get_pagination_params()
    tickets = employee.tickets  
    
    # Custom pagination for already loaded collection
    total_items = len(tickets)
    paginated_tickets = tickets[(page-1)*limit : page*limit]
    
    pagination = {
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": (total_items + limit - 1) // limit,
        "has_next": page * limit < total_items,
        "has_prev": page > 1
    }

    # Imported here to avoid circular import!
    from application.blueprints.service_ticket.schemas import service_tickets_schema
    return success_response(data=service_tickets_schema.dump(paginated_tickets), meta={"pagination": pagination})

# ---- Get mechanics by ticket count ----
@employee_bp.route('/by-ticket-count', methods=['GET'])
@token_required
def get_mechanics_by_ticket_count(user_id):
    results = db.session.query(
        Employee, func.count(ServiceTicket.id).label('ticket_count')
    ).join(employee_service_ticket, Employee.id == employee_service_ticket.c.mechanic_id
    ).join(ServiceTicket, ServiceTicket.id == employee_service_ticket.c.service_ticket_id
    ).group_by(Employee.id
    ).order_by(func.count(ServiceTicket.id).desc()).all()

    data = [{"id": emp.id, "name": emp.name, "ticket_count": count} for emp, count in results]
    return success_response(data=data)

# MARK: PUT 
# -----Update Employee----
@employee_bp.route('/<int:id>', methods=['PUT'])
@token_required
def update_employee(user_id, id):
    try:
        employee = db.session.get(Employee, id)
        if not employee:
            return error_response("Employee not found", 404)

        data = request.json
        
        # FULL validation so mo missing required fields
        validated_data = employee_schema.load(data)
        
        # update employee atribute dynamizly
        for key, value in data.items():
            if key == "password" and value:
                employee.password = hash_password(value)
            elif hasattr(employee, key): # checks if the model has this attribute
                setattr(employee, key, value) # if yes updates the attribute

        db.session.commit()
        return success_response(data=employee_schema.dump(employee))
    
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# MARK: Partial Update Employee
@employee_bp.route('/<int:id>', methods=['PATCH'])
@token_required
def partial_update_employee(user_id, id):
    try:
        employee = db.session.get(Employee, id)
        if not employee:
            return error_response("Employee not found", 404)

        data = request.json
        
        # Skip validation if not needed
        if not data:
            return success_response(data=employee_schema.dump(employee))
            
        # Lallow missing fields
        try:
            validated_data = employee_schema.load(data, partial=True)
            
            # If validated_data is a model instance, convert to dict
            if not isinstance(validated_data, dict):
                validated_data = employee_schema.dump(validated_data)
                
            for key, value in data.items():
                if key == "password" and value:
                    employee.password = hash_password(value)
                elif hasattr(employee, key):
                    setattr(employee, key, value)

            db.session.commit()
            return success_response(data=employee_schema.dump(employee))
        except ValidationError as err:
            return validation_error_response(err)

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# MARK: Delete 
@employee_bp.route('/<int:id>', methods=['DELETE'])
@token_required
@limiter.limit("5 per hour")
def delete_employee(user_id, id):
    employee = db.session.get(Employee, id)
    if not employee:
        return error_response("Employee not found", 404)

    db.session.delete(employee)
    db.session.commit()
    return success_response(message="Employee deleted successfully")