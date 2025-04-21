from marshmallow import fields, validate
from application.extensions import ma
from application.models import Inventory, SerializedPart

class InventorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Inventory
        # include_relationships = True
        load_instance = True
        
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    price = fields.Decimal(required=True, as_string=True)
    quantity_in_stock = fields.Int(required=True, validate=validate.Range(min=0))
    
inventory_schema = InventorySchema()
inventories_schema = InventorySchema(many=True)

###
class SerializedPartSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SerializedPart
        load_instance = True
        include_fk = True
        
    id = fields.Int(dump_only=True)
    serial_number = fields.Str(required=True)
    status = fields.Str(required=True,validate=validate.OneOf(["available", "used", "defective"]))
    inventory_id = fields.Int(required=True)
    
    inventory = fields.Nested(
        InventorySchema(only=("id", "name", "inventory_number", "price", "desc")),
        dump_only=True
    )
        
serialized_part_schema = SerializedPartSchema()
serialized_parts_schema = SerializedPartSchema(many=True) 
