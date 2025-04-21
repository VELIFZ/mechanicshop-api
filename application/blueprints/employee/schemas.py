from marshmallow import fields
from application.extensions import ma
from application.models import Employee
from marshmallow.validate import Email

class EmployeeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Employee
        load_instance = True

    id = fields.Int(dump_only=True)
    password = fields.String(load_only=True, allow_none=True)
    email = fields.Email(required=True, validate=Email(error="Invalid email format"))
        
employee_schema = EmployeeSchema()
employees_schema = EmployeeSchema(many=True)
