from flask import request, jsonify
from . import service_bp
from marshmallow import ValidationError
from application.utils import validation_error_response, error_response
from sqlalchemy import select
from application.models import Service, db
from application.blueprints.service_.schemas import service_schema, services_schema


@service_bp.route("/", methods=["POST"])
def create_service():
    try:
        service_data = service_schema.load(request.json)
        
        # Normalize service_type
        service_data["service_type"] = service_data["service_type"].title()
        
        # Check for duplicates (normalized)
        existing = db.session.query(Service).filter_by(service_type=service_data["service_type"], description=service_data["description"]).first()
        if existing:
            return error_response("Service with this type and description already exists.", 400)
        
        new_service= Service(**service_data)
        db.session.add(new_service)
        db.session.commit()
        return jsonify(service_schema.dump(new_service)), 201
    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    

@service_bp.route('/', methods=['GET'])
def get_all_services():
    query = db.session.query(Service)
    services = db.session.execute(query).scalars().all()
    return jsonify(services_schema.dump(services)), 200

@service_bp.route('/<int:service_id>', methods=['GET'])
def get_single_service(service_id):
    service = db.session.query(Service).get(service_id)
    if not service:
        return error_response("Service not found", 404)
    return jsonify(service_schema.dump(service)), 200

# UPDATE
@service_bp.route('/<int:service_id>', methods=['PUT'])
def update_service(service_id):
    try:
        service_data = service_schema.load(request.json)
        service_data["service_type"] = service_data["service_type"].title()

        service = db.session.get(Service, service_id)
        if not service:
            return error_response("Service not found", 404)

        for key, value in service_data.items():
            setattr(service, key, value)

        db.session.commit()
        return service_schema.dump(service), 200

    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
# PATCH
@service_bp.route('/<int:service_id>', methods=['PATCH'])
def partially_update_service(service_id):
    try:
        service = db.session.get(Service, service_id)
        
        if not service:
            return error_response("Service not found", 404)
        
        updated_data = service_schema.load(request.get_json(), partial=True)
        
        if "service_type" in updated_data:
            updated_data["service_type"] = updated_data["service_type"].title()
        
        for key, value in updated_data.items():
            setattr(service, key, value)
            
        db.session.commit()
        return jsonify(service_schema.dump(service)), 200
    
    except ValidationError as err:  
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
              
# DELETE
@service_bp.route('/<int:service_id>', methods=['DELETE'])
def delete_service(service_id):
    
    query = select(Service).where(Service.id == service_id)
    service = db.session.execute(query).scalars().first()
    
    if not service:
        return error_response("Service not found", 404)
    
    db.session.delete(service)
    db.session.commit()
    return jsonify({"message": f"{service.id} deleted successfully"}), 204




## service type filtering? services?type=oil