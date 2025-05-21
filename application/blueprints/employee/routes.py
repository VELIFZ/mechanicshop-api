from flask import request, jsonify
from . import employee_bp
from application.models import Employee, Customer, ServiceTicket, employee_service_ticket, db
from application.blueprints.employee.schemas import employee_schema, employees_schema, login_schema
from application.blueprints.customer.schemas import customer_schema, customers_schema
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
        # Get request data
        request_json = request.get_json()
        if not request_json:
            return error_response("Missing request data", 400)
            
        # Validate credentials
        credentials = login_schema.load(request_json)
        if not credentials.get('email') or not credentials.get('password'):
            return error_response("Email and password are required", 400)
            
        # Find employee
        employee = db.session.query(Employee).filter_by(email=credentials['email'].lower()).first()

        if employee and verify_password(employee.password, credentials['password']):
            token = encode_token(employee.id, 'employee')
            return success_response(message="Successfully logged in", data={"token": token})

        return error_response("Invalid email or password", 401)

    except ValidationError as e:
        return validation_error_response(e)
    except Exception as e:
        return error_response(f"Login error: {str(e)}", 500)

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
# ------GET All Employees------ / probably admin level access in the future 
@employee_bp.route('/', methods=['GET'])
@token_required(expected_role='employee')
@cache.cached(timeout=60)
def get_employees(user_id):
    page, limit, sort_by, sort_order = get_pagination_params()
    
    if sort_by not in ["id", "name", "email", "phone", "role", "salary"]:
        return error_response("Invalid query parameter", 400)
    
    query = db.session.query(Employee)
    filter_params = {key: request.args.get(key) for key in ('name', 'email', 'role')}
    query = apply_filters(query, Employee, filter_params)
    
    search = request.args.get('search')
    if search:
        search = f"%{search}%"
        query = query.filter(
            (Employee.name.ilike(search)) |
            (Employee.email.ilike(search)) |
            (Employee.role.ilike(search))
        )
        
    employees, pagination = paginate_query(query, Employee, page, limit, sort_by, sort_order)
    return success_response(data=employees_schema.dump(employees), meta={"pagination": pagination})

# ------GET All Customers------ / admin view 
# get curtomer with Pagination, Filter, and Sort
@employee_bp.route('/customers', methods=['GET'])
@cache.cached(timeout=60)
@token_required(expected_role="employee")
def get_customers(user_id):
    page, limit, sort_by, sort_order = get_pagination_params()
    
    if sort_by not in ["id", "name", "email", "phone"]:
        return error_response("Invalid query parameter", 400)
    
    # Start with base query
    query = db.session.query(Customer)
    # Apply filters
    filter_params = {'name': request.args.get('name'), 'email': request.args.get('email')}
    query = apply_filters(query, Customer, filter_params)
    
    search = request.args.get('search')
    if search:
        search = f"%{search}%"
        query = query.filter(
            (Customer.name.ilike(search)) |
            (Customer.email.ilike(search))
        )
    
    # Apply pagination + sorting
    customers, pagination = paginate_query(query, Customer, page, limit, sort_by, sort_order)
    return success_response(data=customers_schema.dump(customers), meta={"pagination": pagination})

# ---- Get by ID / Employee ----
@employee_bp.route('/<int:id>', methods=['GET'])
@token_required(expected_role="employee")
def get_employee(user_id, id):   
    employee = db.session.get(Employee, id)
    if not employee:
        return error_response("Employee not found", 404)
    return success_response(data=employee_schema.dump(employee))

# ---get by ID /Customer---
@employee_bp.route('/customers/<int:customer_id>', methods=['GET'])
@token_required(expected_role="employee")
def get_single_customer_as_employee(user_id, customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return error_response("Customer not found", 404)
    return success_response(data=customer_schema.dump(customer))
    
# ---- Profile ------
@employee_bp.route('/me', methods=['GET'])
@limiter.limit("10 per minute")
@token_required(expected_role="employee")
def get_my_profile(user_id):
    employee = db.session.get(Employee, user_id)
    if employee is None:
        return error_response("Employee not found", 404)
    return success_response(data=employee_schema.dump(employee))

# ---- Get Own Tickets ----
@employee_bp.route('/me/tickets', methods=['GET'])
@token_required(expected_role="employee")
@limiter.limit("10 per minute")
def get_my_tickets(user_id):
    employee = db.session.get(Employee, user_id)
    if not employee:
        return error_response("Employee not found", 404)

    page, limit, sort_by, sort_order = get_pagination_params()
    query = db.session.query(ServiceTicket).join(
        employee_service_ticket,
        ServiceTicket.id == employee_service_ticket.c.service_ticket_id
        ).filter( employee_service_ticket.c.mechanic_id == user_id)

    total_items = query.count()
    # memory efficint
    paginated_tickets = query.offset((page-1)*limit).limit(limit).all()

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
@token_required(expected_role="employee")
def get_mechanics_by_ticket_count(user_id):
    ticket_count = func.count(ServiceTicket.id).label('ticket_count')

    results = db.session.query(
        Employee.id, Employee.name, ticket_count
    ).join(employee_service_ticket, Employee.id == employee_service_ticket.c.mechanic_id
    ).join(ServiceTicket, ServiceTicket.id == employee_service_ticket.c.service_ticket_id
    ).group_by(Employee.id, Employee.name
    ).order_by(ticket_count.desc()).all()

    data = [{"id": id, "name": name, "ticket_count": count} for id, name, count in results]
    return success_response(data=data)

# MARK: PUT 
# -----Update Employee----
@employee_bp.route('/<int:id>', methods=['PUT'])
@token_required(expected_role="employee")
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

# MARK: PATCH
# Partial Update Employee
@employee_bp.route('/<int:id>', methods=['PATCH'])
@token_required(expected_role="employee")
def partial_update_employee(user_id, id):
    try:
        employee = db.session.get(Employee, id)
        if not employee:
            return error_response("Employee not found", 404)

        data = request.json
        
        if "role" in data:
            return error_response("You are not allowed to update role", 403)
        
        # Skip validation if not needed
        if not data:
            return success_response(data=employee_schema.dump(employee))
            
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

# ---- Pacth Customer -----
@employee_bp.route('/customers/<int:customer_id>', methods=['PATCH'])
@token_required(expected_role="employee")
def update_customer_as_employee(user_id, customer_id):
    try:
        customer = db.session.get(Customer, customer_id)
        if not customer:
            return error_response("Customer not found", 404)

        data = request.json

        if not data:
            return success_response(data=customer_schema.dump(customer))
        
        # allow missing fields
        try:
            validated_data = customer_schema.load(data, partial=True)

            # Ensure validated_data is a dict
            if not isinstance(validated_data, dict):
                validated_data = customer_schema.dump(validated_data)

            for key, value in data.items():
                if key == "password" and value:
                    customer.password = hash_password(value)
                elif hasattr(customer, key):
                    setattr(customer, key, value)

            db.session.commit()
            return success_response(data=customer_schema.dump(customer))

        except ValidationError as err:
            return validation_error_response(err)

    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
# MARK: Delete 
@employee_bp.route('/<int:id>', methods=['DELETE'])
@token_required(expected_role="employee")
@limiter.limit("5 per hour")
def delete_employee(user_id, id):
    employee = db.session.get(Employee, id)
    if not employee:
        return error_response("Employee not found", 404)

    db.session.delete(employee)
    db.session.commit()
    return success_response(message="Employee deleted successfully")