from flask import request, jsonify
from . import service_ticket_bp
from application.models import db, ServiceTicket, Employee, Service, SerializedPart
from application.blueprints.service_ticket.schemas import service_ticket_schema, service_tickets_schema
from datetime import datetime
from decimal import Decimal


# POST
@service_ticket_bp.route('/', methods=['POST'])
def create_service_ticket():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No input data provided"}), 400
        
        # Loading the base ticket
        ticket = service_ticket_schema.load(data)
        
        # set closed_at if status is "closed"
        if ticket.status == "closed" and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
            
        #? attaching related objects via ids - do i neeed it?
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
                * Decimal("1.06"), 2
            )
        else:
            # estimate = round(
            #     sum(service.base_price for service in ticket.services) +
            #     sum(part.inventory.price for part in ticket.serialized_parts), 2
            # )
            ticket.cost = Decimal("0.00") #-for db store
        
        
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify(service_ticket_schema.dump(ticket)), 201
    
    except Exception as err:
        return jsonify({"message": "Validation Error", "errors": str(err)}), 422

#GET
@service_ticket_bp.route("/", methods=["GET"])
def get_all_tickets():
    try:
        tickets = db.session.query(ServiceTicket).filter_by(is_deleted=False).all()
        
        if not tickets:
            return jsonify({"message": "No service tickets found."}), 404

        return jsonify(service_tickets_schema.dump(tickets)), 200

    except Exception as err:
        return jsonify({
            "message": "An error occurred while fetching service tickets.",
            "error": str(err)
        }), 500

# get by id
@service_ticket_bp.route("/<int:id>", methods=["GET"])
def get_ticket(id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return jsonify({"error": "Not found"}), 404
    return service_ticket_schema.jsonify(ticket)


# PATCH
@service_ticket_bp.route("/<int:id>", methods=["PATCH"])
def update_service_ticket(id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return jsonify({"error": "Service ticket not found."}), 404

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
                 sum(p.inventory.price for p in ticket.serialized_parts)) * Decimal("1.06"), 2
            )
            for part in ticket.serialized_parts:
                part.status = "used"
                if part.inventory and part.inventory.quantity_in_stock > 0:
                    part.inventory.quantity_in_stock -= 1

        db.session.commit()
        return jsonify(service_ticket_schema.dump(ticket)), 200

    except Exception as err:
        return jsonify({"message": "Update failed", "error": str(err)}), 422


# DELETE (soft) - saved for audit and whatever needed
@service_ticket_bp.route("/<int:id>", methods=["DELETE"])
def soft_delete_service_ticket(id):
    ticket = db.session.get(ServiceTicket, id)
    if not ticket or ticket.is_deleted:
        return jsonify({"error": "Service ticket not found"}), 404

    try:
        ticket.is_deleted = True
        db.session.commit()
        return jsonify({"message": "Service ticket soft-deleted"}), 200
    except Exception as err:
        db.session.rollback()
        return jsonify({"error": str(err)}), 500








# paathc to update status open -> close, updating work summary, chaneging the mechanic works on it or add mechanic, add service
#? handel closed at in routes
# should i ecalculate cost only if services or parts changed?

#! don't forget to adjust quantity of inventory after service is completed in here 
#! and update inventory status to "in use" or something like that





