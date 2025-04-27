from flask import request, jsonify
from . import service_bp
from marshmallow import ValidationError
from application.utils.utils import validation_error_response, error_response, token_required
from sqlalchemy import select
from application.models import Service, db
from application.blueprints.service_.schemas import service_schema, services_schema
from application.extensions import cache, limiter


@service_bp.route("/", methods=["POST"])
@token_required
def create_service(user_id):
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
    
# GET
# with ?service_type=Oil, ?page=1&limit=10
@service_bp.route('/', methods=['GET'])
@cache.cached(timeout=60)
def get_all_services():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        service_type_filter = request.args.get('service_type')

        query = db.session.query(Service)

        if service_type_filter:
            query = query.filter(Service.service_type.ilike(f"%{service_type_filter}%"))

        services = query.offset((page - 1) * limit).limit(limit).all()
        return jsonify(services_schema.dump(services)), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# get by id
@service_bp.route('/<int:service_id>', methods=['GET'])
def get_single_service(service_id):
    service = db.session.query(Service).get(service_id)
    if not service:
        return error_response("Service not found", 404)
    return jsonify(service_schema.dump(service)), 200

# UPDATE
@service_bp.route('/<int:service_id>', methods=['PUT'])
@token_required
def update_service(user_id, service_id):
    try:
        service_data = service_schema.load(request.json)
        service_data["service_type"] = service_data["service_type"].title()

        service = db.session.get(Service, service_id)
        if not service:
            return error_response("Service not found", 404)

        for key, value in service_data.items():
            setattr(service, key, value)

        db.session.commit()
        return jsonify(service_schema.dump(service)), 200

    except ValidationError as err:
        return validation_error_response(err)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
# PATCH
@service_bp.route('/<int:service_id>', methods=['PATCH'])
@token_required
def partially_update_service(user_id, service_id):
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
@token_required
def delete_service(user_id, service_id):
    
    query = select(Service).where(Service.id == service_id)
    service = db.session.execute(query).scalars().first()
    
    if not service:
        return error_response("Service not found", 404)
    
    db.session.delete(service)
    db.session.commit()
    # For 204 responses, don't return a body as per HTTP standard
    return "", 204
