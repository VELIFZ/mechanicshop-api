from flask import request, jsonify
from . import service_ticket_bp
from application.models import db, ServiceTicket, Employee, Service, SerializedPart
from application.blueprints.service_ticket.schemas import service_ticket_schema, service_tickets_schema
from application.utils.utils import token_required, error_response, validation_error_response
from application.extensions import cache
from datetime import datetime
from decimal import Decimal
from config import Constants

# POST
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
            available_parts = db.session.query(SerializedPart).filter(SerializedPart.id.in_(part_ids), SerializedPart.status == "available").all()

            ticket.serialized_parts = available_parts

        # set the cost before saving!
        if ticket.status == "closed":
            ticket.cost = round(
                (sum(service.base_price for service in ticket.services) +
                sum(part.inventory.price for part in ticket.serialized_parts)) 
                * Constants.TAX_RATE, 2
            )
        else:
            ticket.cost = Decimal("0.00") #-for db storage
        
        
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify(service_ticket_schema.dump(ticket)), 201
    
    except Exception as err:
        db.session.rollback()
        return error_response("Validation Error", 422, {"errors": str(err)})

#GET
@service_ticket_bp.route("/", methods=["GET"])
@cache.cached(timeout=60)
def get_all_tickets():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status_filter = request.args.get('status')
        customer_id_filter = request.args.get('customer_id', type=int)

        query = db.session.query(ServiceTicket).filter_by(is_deleted=False)

        if status_filter:
            query = query.filter(ServiceTicket.status.ilike(f"%{status_filter}%"))

        if customer_id_filter:
            query = query.filter(ServiceTicket.customer_id == customer_id_filter)

        tickets = query.offset((page - 1) * limit).limit(limit).all()

        return jsonify(service_tickets_schema.dump(tickets)), 200

    except Exception as err:
        db.session.rollback()
        return error_response(str(err), 500)

# get by id
@service_ticket_bp.route("/<int:id>", methods=["GET"])
def get_ticket(id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return error_response("Service ticket not found.", 404)
    return jsonify(service_ticket_schema.dump(ticket)), 200


# PATCH
@service_ticket_bp.route("/<int:id>", methods=["PATCH"])
@token_required
def update_service_ticket(user_id, id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return error_response("Service ticket not found.", 404)

    try:
        data = request.get_json()

        if "status" in data:
            ticket.status = data["status"]
            if ticket.status == "closed" and not ticket.closed_at:
                ticket.closed_at = datetime.utcnow()

        if "work_summary" in data:
            ticket.work_summary = data["work_summary"]

        if "employee_ids" in data:
            ticket.employees = db.session.query(Employee).filter(Employee.id.in_(data["employee_ids"])).all()

        if "service_ids" in data:
            ticket.services = db.session.query(Service).filter(Service.id.in_(data["service_ids"])).all()

        if "part_ids" in data:
            ticket.serialized_parts = db.session.query(SerializedPart).filter(SerializedPart.id.in_(data["part_ids"])).all()

        # Finalize cost and parts if closed
        if ticket.status == "closed":
            ticket.cost = round(
                (sum(s.base_price for s in ticket.services) +
                 sum(p.inventory.price for p in ticket.serialized_parts)) * Constants.TAX_RATE, 2
            )
            for part in ticket.serialized_parts:
                part.status = "used"
                if part.inventory and part.inventory.quantity_in_stock > 0:
                    part.inventory.quantity_in_stock -= 1

        db.session.commit()
        return jsonify(service_ticket_schema.dump(ticket)), 200

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
        return jsonify({"status": "success", "message": "Service ticket soft-deleted"}), 200
    except Exception as err:
        db.session.rollback()
        return error_response(str(err), 500)


@service_ticket_bp.route('/<int:ticket_id>/edit', methods=['PUT'])
@token_required
def edit_ticket_mechanics(user_id, ticket_id):
    try:
        ticket = db.session.get(ServiceTicket, ticket_id)
        if not ticket:
            return error_response("Ticket not found", 404)
        
        data = request.get_json()
        remove_ids = data.get('remove_ids', [])
        add_ids = data.get('add_ids', [])
        
        # Remove mechanics
        if remove_ids:
            mechanics_to_remove = db.session.query(Employee).filter(Employee.id.in_(remove_ids)).all()
            for mechanic in mechanics_to_remove:
                if mechanic in ticket.employees:
                    ticket.employees.remove(mechanic)
        
        # Add mechanics
        if add_ids:
            mechanics_to_add = db.session.query(Employee).filter(Employee.id.in_(add_ids)).all()
            for mechanic in mechanics_to_add:
                if mechanic not in ticket.employees:
                    ticket.employees.append(mechanic)
        
        db.session.commit()
        return jsonify(service_ticket_schema.dump(ticket)), 200
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
    
@service_ticket_bp.route('/<int:ticket_id>/add-part/<int:part_id>', methods=['POST'])
@token_required
def add_part_to_ticket(user_id, ticket_id, part_id):
    try:
        ticket = db.session.get(ServiceTicket, ticket_id)
        if not ticket:
            return error_response("Ticket not found", 404)
            
        part = db.session.get(SerializedPart, part_id)
        if not part:
            return error_response("Part not found", 404)
            
        if part.status != "available":
            return error_response("Part is not available", 400)
            
        ticket.serialized_parts.append(part)
        part.status = "used"
        
        db.session.commit()
        return jsonify(service_ticket_schema.dump(ticket)), 200
        
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)