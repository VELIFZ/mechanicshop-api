"""Service schemas for serialization/deserialization"""
from marshmallow import fields
from application.extensions import ma
from application.models import Service

class ServiceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Service
        load_instance = False # So .load() returns a dict
        
    id = fields.Int(dump_only=True)
        
service_schema = ServiceSchema()
services_schema = ServiceSchema(many=True) 

