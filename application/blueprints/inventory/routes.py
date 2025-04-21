from sqlalchemy.exc import IntegrityError
from flask import request, jsonify
from . import inventory_bp
from application.models import Inventory, SerializedPart, db
from application.blueprints.inventory.schemas import inventory_schema, inventories_schema, serialized_part_schema, serialized_parts_schema
from marshmallow import ValidationError
from application.utils import validation_error_response, error_response
from sqlalchemy import select

# POST
@inventory_bp.route('/', methods=['POST'])
def create_inventory():
    try:
        inventory_data = inventory_schema.load(request.json)
        db.session.add(inventory_data)
        db.session.commit()
        return jsonify(inventory_schema.dump(inventory_data)), 201
        
    except ValidationError as err:
        return validation_error_response(err)
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": {"inventory_number": ["This inventory number already exists."]}}), 400
    except Exception as e:
        print(f" Inventory creation error: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GET -> /?deleted=true
@inventory_bp.route('/', methods=['GET'])
def get_inventory():
    try:
        deleted_filter = request.args.get("deleted")

        if deleted_filter == "true":
            inventory_items = db.session.query(Inventory).filter_by(is_deleted=True).all()
        else:
            inventory_items = db.session.query(Inventory).filter_by(is_deleted=False).all()

        return jsonify(inventories_schema.dump(inventory_items)), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# GET by id 
@inventory_bp.route('/<int:inventory_id>', methods=['GET'])
def get_inventory_by_id(inventory_id):
    try:
        inventory = db.session.get(Inventory, inventory_id)
        if inventory is None or inventory.is_deleted:
            return jsonify({"error": "Inventory not found"}), 404
        
        return jsonify(inventory_schema.dump(inventory)), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# soft delete    
@inventory_bp.route('/<int:inventory_id>', methods=['DELETE'])
def delete_inventory(inventory_id):
    try:
        inventory = db.session.get(Inventory, inventory_id)
        if not inventory or inventory.is_deleted:
            return jsonify({"error": "Inventory not found"}), 404

        inventory.is_deleted = True
        db.session.commit()
        return jsonify({"message": "Inventory deleted (soft)"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
 
 
    
#MARK: Serialized Part
# POST
@inventory_bp.route('/serialized-parts/', methods=['POST'])
def create_serialized_part():
    try:
        data = serialized_part_schema.load(request.json)
        inventory = db.session.get(Inventory, data.inventory_id)
        
        if not inventory:
            return jsonify({ "errors": {"inventory_id": ["Inventory not found."]}}), 400
        
        db.session.add(data)
        db.session.commit()
        return jsonify(serialized_part_schema.dump(data)), 201
    
    except ValidationError as err:
        print(" ValidationError:", err.messages)  
        return validation_error_response(err)
    
    except IntegrityError:
        db.session.rollback()
        return jsonify({"errors": {"serial_number": ["This serialized part already exists."]}}), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
        
# GET
@inventory_bp.route('/serialized-parts/', methods=['GET'])
def get_serialized_parts():
    
    parts = db.session.execute(select(SerializedPart)).scalars().all()
    return jsonify(serialized_parts_schema.dump(parts)), 200

# by id    
@inventory_bp.route('/serialized-parts/<int:part_id>', methods=['GET'])
def get_serialized_parts_by_id(part_id):
    part = db.session.get(SerializedPart, part_id)
    
    if not part:
        return jsonify({'error': "Serialized part not found"}), 404
    return jsonify(serialized_part_schema.dump(part)), 200

# PATCH but only status
@inventory_bp.route('/serialized-parts/<int:part_id>', methods=['PATCH'])
def update_serialized_part_status(part_id):
    
    part = db.session.get(SerializedPart, part_id)
    if not part:
        return jsonify({"error": "Serialized part not found"}), 404
    
    new_status = request.json.get('status')
    if new_status not in ["available", "used", "defective"]:
        return jsonify({'errors': {'status': ['Invalid status value.']}}), 400
    
    part.status = new_status
    db.session.commit()
    
    return jsonify(serialized_part_schema.dump(part)), 200





#? add later - filter or search by status -> ?status=available

    
#! inventory usually does not need updated (since it's scaned), only created or deleted(?)  ---- or do i add one for price changes?
#!  will update the quantity in service ticket route 
