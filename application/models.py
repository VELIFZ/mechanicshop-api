from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Enum

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Association table for Employee-ServiceTicket many-to-many relationship (M:M)
employee_service_ticket = db.Table(
    "employee_service_ticket",
    Base.metadata,
    db.Column("mechanic_id", db.Integer, db.ForeignKey("employee.id"), primary_key=True),
    db.Column("service_ticket_id", db.Integer, db.ForeignKey("service_ticket.id"), primary_key=True),
)

# Association table for SerializedPart-ServiceTicket many-to-many relationship (M:M)
serialized_part_usage = db.Table(
    "serialized_part_usage",
    Base.metadata,
    db.Column("serialized_part_id", db.Integer, db.ForeignKey("serialized_part.id"), primary_key=True),
    db.Column("service_ticket_id", db.Integer, db.ForeignKey("service_ticket.id"), primary_key=True),
    # Enforce uniqueness at the DB level to restrict each serialized part to only one service ticket
    # This ensures business logic (one-time use) is backed by schema constraint
    db.UniqueConstraint("serialized_part_id", name="uq_serialized_part_once_used")
)

#  Dependent table for Service-ServiceTicket (1:M via dependent join table)
service_tracker = db.Table(
    "service_tracker",
    Base.metadata,
    #db.Column("id", db.Integer, primary_key=True),
    db.Column("service_id", db.Integer, db.ForeignKey("service.id")),
    db.Column("service_ticket_id", db.Integer, db.ForeignKey("service_ticket.id"))
)

#MARK: Customer Model
class Customer(Base):
    __tablename__ = "customer"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(50))
    email: Mapped[str] = mapped_column(db.String(100), unique=True)
    phone: Mapped[str] = mapped_column(db.String(20))
    
    # Relationship - Customer -> ServiceTicket (1:M)
    # One customer can have many service tickets
    tickets: Mapped[List["ServiceTicket"]] = relationship(back_populates="customer")
 
#MARK: Employee Model
class Employee(Base):
    __tablename__ = "employee"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(50))
    email: Mapped[str] = mapped_column(db.String(100), unique=True)
    phone: Mapped[str] = mapped_column(db.String(20))
    password: Mapped[str] = mapped_column(db.String(20))
    salary: Mapped[float] = mapped_column(db.DECIMAL(10, 2))
    role: Mapped[str] = mapped_column(db.String(50))
    # address: Mapped[str] = mapped_column(db.String(200))
    
    # Relationship - Employee <-> ServiceTicket (M:M)
    # An employee can work on many service tickets
    # A service ticket can have many employees working on it
    tickets: Mapped[List["ServiceTicket"]] = relationship( secondary=employee_service_ticket, back_populates="employees")

#MARK: Inventory Model
class Inventory(Base):
    __tablename__ = "inventory"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    inventory_number: Mapped[str] = mapped_column(db.String(50), unique=True)
    price: Mapped[float] = mapped_column(db.DECIMAL(10, 2), nullable=False)
    desc: Mapped[str] = mapped_column(db.String(200))
    quantity_in_stock: Mapped[int] = mapped_column(db.Integer)
    is_deleted: Mapped[bool] = mapped_column(db.Boolean, default=False)
    
    # Relationship - Inventory -> SerializedPart (1:M)
    # One inventory item can have many serialized parts
    serialized_parts: Mapped[List["SerializedPart"]] = relationship(back_populates="inventory", cascade="all, delete-orphan")

#MARK: SerializedPart Model
class SerializedPart(Base):
    __tablename__ = "serialized_part"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(db.String(50), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(db.String(20))  # available, used, defective # do enum
    
    # Foreign key - SerializedPart -> Inventory (M:1)
    inventory_id: Mapped[int] = mapped_column(db.ForeignKey("inventory.id"), nullable=False)
    
    # Relationship - SerializedPart -> Inventory (M:1) 
    # Many serialized parts belong to one inventory item
    inventory: Mapped["Inventory"] = relationship(back_populates="serialized_parts")
    
    # Relationship - SerializedPart <-> ServiceTicket (M:M)
    # A serialized part is usually used in one service ticket (business logic enforces this), but technically M:M.
    # A service ticket can include many serialized parts. Each serialized part is typically used in only one ticket.
    service_tickets: Mapped[List["ServiceTicket"]] = relationship(secondary=serialized_part_usage, back_populates="serialized_parts")

#MARK: Service Model
class Service(Base):
    __tablename__ = "service"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    service_type: Mapped[str] = mapped_column(db.String(100))
    base_price: Mapped[float] = mapped_column(db.DECIMAL(10, 2))
    description: Mapped[str] = mapped_column(db.String(200))
    
    # Relationship - Service -> ServiceTicket (via dependent service_tracker)
    # Even tho service_ticket owns service because of busniss logic it's M:M 
    tickets: Mapped[List["ServiceTicket"]] = relationship(secondary=service_tracker, back_populates="services")

#MARK: ServiceTicket Model
class ServiceTicket(Base):
    __tablename__ = "service_ticket"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    vin: Mapped[str] = mapped_column(db.String(17), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(db.DateTime, nullable=True)
    work_summary: Mapped[str] = mapped_column(db.Text, nullable=False)
    cost: Mapped[float] = mapped_column(db.DECIMAL(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(Enum('open', 'in_progress', 'closed', name='service_ticket_status'), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(db.Boolean, default=False)
    
    # Foreign key - ServiceTicket -> Customer (M:1)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey("customer.id"), nullable=False)
    
    # Relationship - ServiceTicket -> Customer (M:1)    
    # Many service tickets belong to one customer
    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    
    # Relationship - ServiceTicket <-> Employee (M:M)
    # A service ticket can have many employees working on it
    # An employee can work on many service tickets
    employees: Mapped[List["Employee"]] = relationship(secondary=employee_service_ticket, back_populates="tickets")
    
    # Relationship - ServiceTicket <-> SerializedPart (M:M)
    # A service ticket can use many serialized parts
    # A serialized part can be used in one service ticket 
    serialized_parts: Mapped[List["SerializedPart"]] = relationship(secondary=serialized_part_usage, back_populates="service_tickets",)
    
    # Relationship - ServiceTicket -> Service (1:M) (actually M:M)
    services: Mapped[List["Service"]] = relationship(secondary=service_tracker, back_populates="tickets")
    
    