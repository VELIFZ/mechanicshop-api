from marshmallow import fields
from application.extensions import ma
from application.models import Employee
from marshmallow.validate import Email
from marshmallow.validate import Email, Length, Regexp

class EmployeeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Employee
        load_instance = True

    id = fields.Int(dump_only=True)
    password = fields.String(load_only=True, allow_none=True)
    email = fields.Email(required=True, validate=Email(error="Invalid email format"))
    phone = fields.String(required=True, validate=[Length(equal=10), Regexp(r'^\d{10}$', error="Invalid phone format")])

class LoginSchema(ma.Schema):
    email = fields.Email(required=True, validate=Email(error="Invalid email format"))
    password = fields.String(required=True)
        
employee_schema = EmployeeSchema()
employees_schema = EmployeeSchema(many=True)
login_schema = LoginSchema()
