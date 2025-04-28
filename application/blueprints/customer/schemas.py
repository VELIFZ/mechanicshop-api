from marshmallow import fields, ValidationError, validates, pre_load
from marshmallow.validate import Email, Length, Regexp
from application.extensions import ma
from application.models import Customer
from application.utils.utils import is_strong_password

class CustomerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Customer
        load_instance = False

    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)
    phone = fields.String(required=True, validate=[Length(equal=10), Regexp(r'^\d{10}$', error="Invalid phone format")])
    
    @pre_load
    def normalize_email(self, data, **kwargs):
        if "email" in data and isinstance(data["email"], str):
            data["email"] = data["email"].lower().strip()
        return data

    @validates('password')
    def validate_password_strength(self, value):
        if not is_strong_password(value):
            raise ValidationError("Password must be at least 8 characters long, including letters and numbers.")
        
customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)
login_schema = CustomerSchema(exclude=['name', 'phone'])
