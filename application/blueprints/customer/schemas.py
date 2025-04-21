from marshmallow import fields
from marshmallow.validate import Email
from application.extensions import ma
from application.models import Customer

class CustomerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Customer
        load_instance = False

    id = fields.Int(dump_only=True)
    email = fields.Email(required=True, validate=Email(error="Invalid email format"))
    # phone validation
        
customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

