from flask import request, jsonify
from . import service_ticket_bp
from application.models import db, ServiceTicket, Employee, Service, SerializedPart
from application.blueprints.service_ticket.schemas import service_ticket_schema, service_tickets_schema
from application.utils.utils import (
    token_required, error_response, calculate_ticket_cost,
    success_response, get_pagination_params, paginate_query
)
from application.extensions import cache
from datetime import datetime
from decimal import Decimal
from marshmallow import ValidationError

# POST - create a new service ticket
@service_ticket_bp.route('/', methods=['POST'])
@token_required
def create_service_ticket(user_id):
    try:
        data = request.get_json()
        if not data:
            return error_response("No input data provided", 400)
        
        # Loading the base ticket
        ticket = service_ticket_schema.load(data)
        
        # set closed_at if status is "closed"
        if ticket.status == "closed" and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
        
        # attaching related objects via ids    
        employee_ids = data.get("employee_ids", [])
        service_ids = data.get("service_ids", [])
        part_ids = data.get("part_ids", [])
            
        if employee_ids:
            ticket.employees = db.session.query(Employee).filter(Employee.id.in_(employee_ids)).all()

        if service_ids:
            ticket.services = db.session.query(Service).filter(Service.id.in_(service_ids)).all()

        if part_ids:
            # Only get parts that are available
            available_parts = db.session.query(SerializedPart).filter(
                SerializedPart.id.in_(part_ids), 
                SerializedPart.status == "available"
            ).all()
            
            # Check if all requested parts are available
            if len(available_parts) != len(part_ids):
                return error_response("Some parts are not available", 422)
                
            ticket.serialized_parts = available_parts
            
            # If status is closed, update parts status to used
            if ticket.status == "closed":
                for part in ticket.serialized_parts:
                    part.status = "used"

        # set the cost before saving!
        if ticket.status == "closed":
            ticket.cost = calculate_ticket_cost(ticket.services, ticket.serialized_parts)
        else:
            ticket.cost = Decimal("0.00") #-for db storage
        
        
        db.session.add(ticket)
        db.session.commit()
        
        return success_response(
            message="Service ticket created successfully",
            data=service_ticket_schema.dump(ticket),
            status_code=201
        )
    
    except Exception as err:
        db.session.rollback()
        return error_response("Validation Error", 422, {"errors": str(err)})

#GET - get all service tickets
@service_ticket_bp.route("/", methods=["GET"])
@cache.cached(timeout=60)
def get_all_tickets():
    try:
        page, limit, sort_by, sort_order = get_pagination_params()
        
        # Start with base query, filtering out deleted tickets
        query = db.session.query(ServiceTicket).filter_by(is_deleted=False)
        
        # Apply filters
        filter_params = {
            'status': request.args.get('status'),
            'customer_id': request.args.get('customer_id', type=int)
        }
        
        # Handle special case for string ilike filters manually
        status_filter = request.args.get('status')
        if status_filter:
            query = query.filter(ServiceTicket.status.ilike(f"%{status_filter}%"))
            
        # Handle direct equality filters
        customer_id_filter = request.args.get('customer_id', type=int)
        if customer_id_filter:
            query = query.filter(ServiceTicket.customer_id == customer_id_filter)
        
        # Apply pagination
        tickets, pagination = paginate_query(query, ServiceTicket, page, limit, sort_by, sort_order)

        return success_response(
            data=service_tickets_schema.dump(tickets),
            meta={"pagination": pagination}
        )

    except Exception as err:
        db.session.rollback()
        return error_response(str(err), 500)

# get by id
@service_ticket_bp.route("/<int:id>", methods=["GET"])
def get_ticket(id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return error_response("Service ticket not found.", 404)
    return success_response(data=service_ticket_schema.dump(ticket))


# PATCH - partial update a service ticket
@service_ticket_bp.route("/<int:id>", methods=["PATCH"])
@token_required
def update_service_ticket(user_id, id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return error_response("Service ticket not found.", 404)

    try:
        data = request.get_json()

        # 1 - update simple fields
        if "status" in data:
            ticket.status = data["status"]
            if ticket.status == "closed" and not ticket.closed_at:
                ticket.closed_at = datetime.utcnow()

        if "work_summary" in data:
            ticket.work_summary = data["work_summary"]

        # 2- update employee
        if "add_employee_ids" in data and data["add_employee_ids"]:
            new_employees = db.session.query(Employee).filter(Employee.id.in_(data["add_employee_ids"])).all()
            if len(new_employees) != len(data["add_employee_ids"]):
                return error_response("Some employee IDs not found.", 404)
            
            #current employees because set is faster than list - O(1) vs O(n)
            current_employee_ids = {e.id for e in ticket.employees}
            ticket.employees.extend([e for e in new_employees if e.id not in current_employee_ids]) 

        if "remove_employee_ids" in data and data["remove_employee_ids"]:
            remove_employees = db.session.query(Employee).filter(Employee.id.in_(data["remove_employee_ids"])).all()
            if len(remove_employees) != len(data["remove_employee_ids"]):
                return error_response("Some employee IDs to remove not found.", 404)

            for emp in remove_employees:
                if emp in ticket.employees:
                    ticket.employees.remove(emp)

        # 3- update service
        if "add_service_ids" in data:
            new_services = db.session.query(Service).filter(Service.id.in_(data["add_service_ids"])).all()
            if len(new_services) != len(data["add_service_ids"]):
                return error_response("Some service IDs not found.", 404)
            ticket.services.extend([s for s in new_services if s not in ticket.services])

        if "remove_service_ids" in data:
            remove_services = db.session.query(Service).filter(Service.id.in_(data["remove_service_ids"])).all()
            for serv in remove_services:
                if serv in ticket.services:
                    ticket.services.remove(serv)

        # 4- update part
        if "add_part_ids" in data:
            new_parts = db.session.query(SerializedPart).filter(
                SerializedPart.id.in_(data["add_part_ids"]),
                SerializedPart.status == "available"
            ).all()
            if len(new_parts) != len(data["add_part_ids"]):
                return error_response("Some part IDs not found or not available.", 422)
            ticket.serialized_parts.extend([p for p in new_parts if p not in ticket.serialized_parts])


        if "remove_part_ids" in data:
            remove_parts = db.session.query(SerializedPart).filter(
                SerializedPart.id.in_(data["remove_part_ids"])
            ).all()
            for part in remove_parts:
                if part in ticket.serialized_parts:
                    ticket.serialized_parts.remove(part)

        # 5. Final: Update cost if closed
        if ticket.status == "closed":
            ticket.cost = calculate_ticket_cost(ticket.services, ticket.serialized_parts)
            for part in ticket.serialized_parts:
                part.status = "used"
                if part.inventory and part.inventory.quantity_in_stock > 0:
                    part.inventory.quantity_in_stock -= 1

        db.session.commit()
        return success_response(data=service_ticket_schema.dump(ticket))

    except Exception as err:
        db.session.rollback()
        return error_response("Update failed", 422, {"error": str(err)})

# DELETE (soft) - saved for audit and whatever needed
@service_ticket_bp.route("/<int:id>", methods=["DELETE"])
@token_required
def soft_delete_service_ticket(user_id, id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return error_response("Service ticket not found", 404)

    try:
        ticket.is_deleted = True
        db.session.commit()
        return success_response(message="Service ticket soft-deleted")
    except Exception as err:
        db.session.rollback()
        return error_response(str(err), 500)