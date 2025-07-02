from sqlalchemy.exc import IntegrityError
from flask import request, jsonify
from . import inventory_bp
from application.models import Inventory, SerializedPart, db
from application.blueprints.inventory.schemas import inventory_schema, inventories_schema, serialized_part_schema, serialized_parts_schema
from marshmallow import ValidationError
from application.utils.utils import (
    validation_error_response, token_required, error_response,
    success_response, get_pagination_params, paginate_query, apply_filters
)
from application.extensions import cache

# POST - Create inventory item
@inventory_bp.route('/', methods=['POST'])
@token_required(expected_role="employee")
def create_inventory(user_id):
    try:
        inventory_data = inventory_schema.load(request.json)
        db.session.add(inventory_data)
        db.session.commit()
        return success_response(
            message="Inventory item created successfully",
            data=inventory_schema.dump(inventory_data),
            status_code=201
        )
        
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
        page, limit, sort_by, sort_order = get_pagination_params()
        valid_sort_fields = ["id", "inventory_number", "name", "price", "quantity_in_stock"]
        if sort_by and sort_by not in valid_sort_fields:
            return error_response("Invalid sort_by field", 400)

        deleted_filter = request.args.get("deleted") == "true"
        
        # Start with base query
        query = db.session.query(Inventory)
        
        # Filter by deletion status
        query = query.filter(Inventory.is_deleted == deleted_filter)
        
        # Apply filters
        filter_params = {
            'inventory_number': request.args.get('inventory_number'),
            'part_name': request.args.get('part_name')
        }
        query = apply_filters(query, Inventory, filter_params)
        
        # Apply pagination
        items, pagination = paginate_query(query, Inventory, page, limit, sort_by, sort_order)

        return success_response(
            data=inventories_schema.dump(items),
            meta={"pagination": pagination}
        )
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
        
        return success_response(data=inventory_schema.dump(inventory))
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
    
# PATCH 
@inventory_bp.route('/<int:inventory_id>', methods=['PATCH'])
@token_required(expected_role="employee")
def update_inventory(user_id, inventory_id):
    try:
        inventory = db.session.get(Inventory, inventory_id)
        if not inventory or inventory.is_deleted:
            return error_response("Inventory not found", 404)

        update_data = request.json

        # Allow updating specific fields only
        for field in ['price', 'quantity_in_stock']:
            if field in update_data:
                setattr(inventory, field, update_data[field])

        db.session.commit()
        return success_response(data=inventory_schema.dump(inventory))
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# DELETE -soft delete    
@inventory_bp.route('/<int:inventory_id>', methods=['DELETE'])
@token_required(expected_role="employee")
def delete_inventory(user_id, inventory_id):
    try:
        inventory = db.session.get(Inventory, inventory_id)
        if not inventory:
            return error_response("Inventory not found", 404)
        
        if inventory.is_deleted:
            return error_response("Inventory already deleted", 404)

        inventory.is_deleted = True
        db.session.commit()
        
        # Clear cache to ensure fresh data on next request
        cache.clear()
        
        return success_response(message="Inventory deleted (soft)")
    
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
 
 
    
#MARK: Serialized Part
# POST
@inventory_bp.route('/serialized-parts/', methods=['POST'])
@token_required(expected_role="employee")
def create_serialized_part(user_id):
    try:
        data = serialized_part_schema.load(request.json)
        inventory = db.session.get(Inventory, data.inventory_id)
        
        if not inventory:
            return error_response("Inventory not found", 400, {"inventory_id": ["Inventory not found."]})
        
        db.session.add(data)
        db.session.commit()
        return success_response(
            message="Serialized part created successfully",
            data=serialized_part_schema.dump(data),
            status_code=201
        )
    
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
        page, limit, sort_by, sort_order = get_pagination_params()

        # Start with base query
        query = db.session.query(SerializedPart)

        status = request.args.get('status')
        if status:
            query = query.filter(SerializedPart.status == status)

        parts, pagination = paginate_query(query, SerializedPart, page, limit, sort_by, sort_order)

        return success_response(
            data=serialized_parts_schema.dump(parts),
            meta={"pagination": pagination}
        )
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
        return success_response(data=serialized_part_schema.dump(part))
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

# PATCH but only status
@inventory_bp.route('/serialized-parts/<int:part_id>', methods=['PATCH'])
@token_required(expected_role="employee")
def update_serialized_part_status(user_id, part_id):
    try:
        part = db.session.get(SerializedPart, part_id)
        if not part:
            return error_response("Serialized part not found", 404)
        
        if part.is_deleted:
            return error_response("Serialized part not found", 404)
        
        new_status = request.json.get('status')
        if new_status not in ["available", "used", "defective"]:
            return error_response("Invalid status value", 400, {"status": ["Invalid status value."]})
        
        part.status = new_status
        db.session.commit()
        
        return success_response(data=serialized_part_schema.dump(part))
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)


# DELETE (soft delete) 
@inventory_bp.route('/serialized-parts/<int:part_id>', methods=['DELETE'])
@token_required(expected_role="employee")
def delete_serialized_part(user_id, part_id):
    try:
        part = db.session.get(SerializedPart, part_id)
        if not part:
            return error_response("Serialized part not found", 404)
        
        if part.is_deleted:
            return error_response("Serialized part is already deleted", 400)

        
        part.is_deleted = True
        db.session.commit()
        
        # Clear cache to ensure fresh data on next request
        cache.clear()
        
        return success_response(message="Serialized part deleted successfully")
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)
