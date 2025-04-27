from marshmallow import fields, validate
from marshmallow.validate import Email, Length, Regexp
from application.extensions import ma
from application.models import Customer

class CustomerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Customer
        load_instance = False

    id = fields.Int(dump_only=True)
    email = fields.Email(required=True, validate=Email(error="Invalid email format"))
    password = fields.String(required=True, load_only=True)
    phone = fields.String(required=True, validate=[Length(equal=10), Regexp(r'^\d{10}$', error="Invalid phone format")])
        
customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)
login_schema = CustomerSchema(exclude=['name', 'phone'])
