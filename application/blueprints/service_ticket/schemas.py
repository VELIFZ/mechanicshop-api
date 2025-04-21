from marshmallow import fields, validate
from application.extensions import ma
from application.models import ServiceTicket
from application.blueprints.customer.schemas import CustomerSchema
from application.blueprints.employee.schemas import EmployeeSchema
from application.blueprints.service_.schemas import ServiceSchema
from application.blueprints.inventory.schemas import InventorySchema, SerializedPartSchema

class ServiceTicketSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ServiceTicket
        include_relationships = False
        load_instance = True
        include_fk = True

    id = fields.Int(dump_only=True)
    status = fields.String(required=True, validate=validate.OneOf(["open", "in_progress", "closed"]))
    created_at = fields.DateTime(dump_only=True)
    closed_at = fields.DateTime(allow_none=True)
    customer_id = fields.Int(required=True, load_only=True)
    cost =  fields.Float(dump_only=True)
    
    # only used for loading from rquest
    employee_ids = fields.List(fields.Int(), load_only=True)
    service_ids = fields.List(fields.Int(), load_only=True)
    part_ids = fields.List(fields.Int(), load_only=True)
    
    # Only for output nested relationships
    customer = fields.Nested(CustomerSchema(only=("id", "name", "email")), dump_only=True)
    employees = fields.List(fields.Nested(EmployeeSchema(only=("id", "name", "role"))))
    services = fields.List(fields.Nested(ServiceSchema(only=("id", "service_type", "base_price"))))
    inventory = fields.Nested(InventorySchema(only=("id", "name", "price")))
    serialized_parts = fields.List(fields.Nested(SerializedPartSchema(only=("id", "serial_number", "status", "inventory"))))
    
        
service_ticket_schema = ServiceTicketSchema()
service_tickets_schema = ServiceTicketSchema(many=True)

