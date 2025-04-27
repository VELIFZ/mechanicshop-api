from sqlalchemy.exc import IntegrityError
from flask import request, jsonify
from . import inventory_bp
from application.models import Inventory, SerializedPart, db
from application.blueprints.inventory.schemas import inventory_schema, inventories_schema, serialized_part_schema, serialized_parts_schema
from marshmallow import ValidationError
from application.utils.utils import validation_error_response, token_required, error_response
from sqlalchemy import select
from application.extensions import cache

# POST - 
@inventory_bp.route('/', methods=['POST'])
@token_required
def create_inventory(user_id):
    try:
        inventory_data = inventory_schema.load(request.json)
        db.session.add(inventory_data)
        db.session.commit()
        return jsonify(inventory_schema.dump(inventory_data)), 201
        
    except ValidationError as err:
        return validation_error_response(err)
    except IntegrityError:
        db.session.rollback()
        return error_response("This inventory number already exists.", 400, {"inventory_number": ["This inventory number already exists."]})
    except Exception as e:
        print(f" Inventory creation error: {e}")
        db.session.rollback()
        return error_response(str(e), 500)

# GET ?deleted=true &inventory_number=xxx&part_name=xxx&page=1&limit=10
@inventory_bp.route('/', methods=['GET'])
@cache.cached(timeout=60)
def get_inventory():
    try:
        deleted_filter = request.args.get("deleted")
        inventory_number = request.args.get("inventory_number")
        part_name = request.args.get("part_name")
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)

        query = db.session.query(Inventory)

        if deleted_filter == "true":
            query = query.filter(Inventory.is_deleted == True)
        else:
            query = query.filter(Inventory.is_deleted == False)

        if inventory_number:
            query = query.filter(Inventory.inventory_number.ilike(f"%{inventory_number}%"))
        if part_name:
            query = query.filter(Inventory.part_name.ilike(f"%{part_name}%"))

        inventory_items = query.offset((page - 1) * limit).limit(limit).all()

        return jsonify(inventories_schema.dump(inventory_items)), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# GET by id 
@inventory_bp.route('/<int:inventory_id>', methods=['GET'])
@cache.cached(timeout=60)
def get_inventory_by_id(inventory_id):
    try:
        inventory = db.session.get(Inventory, inventory_id)
        if inventory is None or inventory.is_deleted:
            return error_response("Inventory not found", 404)
        
        return jsonify(inventory_schema.dump(inventory)), 200
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
# PATCH 
@inventory_bp.route('/<int:inventory_id>', methods=['PATCH'])
@token_required
def update_inventory(user_id, inventory_id):
    try:
        inventory = db.session.get(Inventory, inventory_id)
        if not inventory or inventory.is_deleted:
            return error_response("Inventory not found", 404)

        update_data = request.json

        # Allow updating specific fields only
        for field in ['price', 'quantity', 'location']:
            if field in update_data:
                setattr(inventory, field, update_data[field])

        db.session.commit()
        return jsonify(inventory_schema.dump(inventory)), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# DELETE -soft delete    
@inventory_bp.route('/<int:inventory_id>', methods=['DELETE'])
@token_required
def delete_inventory(user_id, inventory_id):
    try:
        inventory = db.session.get(Inventory, inventory_id)
        if not inventory:
            return error_response("Inventory not found", 404)
        
        if inventory.is_deleted:
            return error_response("Inventory already deleted", 404)

        inventory.is_deleted = True
        db.session.commit()
        return jsonify({"status": "success", "message": "Inventory deleted (soft)"}), 200
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
 
 
    
#MARK: Serialized Part
# POST
@inventory_bp.route('/serialized-parts/', methods=['POST'])
@token_required
def create_serialized_part(user_id):
    try:
        data = serialized_part_schema.load(request.json)
        inventory = db.session.get(Inventory, data.inventory_id)
        
        if not inventory:
            return error_response("Inventory not found", 400, {"inventory_id": ["Inventory not found."]})
        
        db.session.add(data)
        db.session.commit()
        return jsonify(serialized_part_schema.dump(data)), 201
    
    except ValidationError as err:
        print(" ValidationError:", err.messages)  
        return validation_error_response(err)
    
    except IntegrityError:
        db.session.rollback()
        return error_response("This serialized part already exists", 400, {"serial_number": ["This serialized part already exists."]})
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
        
# GET
@inventory_bp.route('/serialized-parts/', methods=['GET'])
@cache.cached(timeout=60)
def get_serialized_parts():
    try:
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        query = db.session.query(SerializedPart)

        if status:
            query = query.filter(SerializedPart.status == status)

        parts = query.offset((page - 1) * limit).limit(limit).all()

        return jsonify(serialized_parts_schema.dump(parts)), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# by id    
@inventory_bp.route('/serialized-parts/<int:part_id>', methods=['GET'])
@cache.cached(timeout=60)
def get_serialized_parts_by_id(part_id):
    try:
        part = db.session.get(SerializedPart, part_id)
        
        if not part or part.is_deleted:
            return error_response("Serialized part not found", 404)
        return jsonify(serialized_part_schema.dump(part)), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# PATCH but only status
@inventory_bp.route('/serialized-parts/<int:part_id>', methods=['PATCH'])
@token_required
def update_serialized_part_status(user_id, part_id):
    try:
        part = db.session.get(SerializedPart, part_id)
        if not part:
            return error_response("Serialized part not found", 404)
        
        new_status = request.json.get('status')
        if new_status not in ["available", "used", "defective"]:
            return jsonify({'errors': {'status': ['Invalid status value.']}}), 400
        
        part.status = new_status
        db.session.commit()
        
        return jsonify(serialized_part_schema.dump(part)), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


# DELETE (soft delete) 
@inventory_bp.route('/serialized-parts/<int:part_id>', methods=['DELETE'])
@token_required
def delete_serialized_part(user_id, part_id):
    try:
        part = db.session.get(SerializedPart, part_id)
        if not part or part.is_deleted:
            return error_response("Serialized part not found", 404)

        part.is_deleted = True
        db.session.commit()
        return jsonify({"status": "success", "message": "Serialized part deleted (soft)"}), 200
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
