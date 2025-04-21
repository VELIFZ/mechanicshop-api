# Mechanic Shop API

A basic service ticket system with customers, mechanics, parts, and services. Built with Flask, SQLAlchemy, and Marshmallow.

## Features

-  CRUD for Employees
-  CRUD for Services
-  CRUD for Inventory & Serialized Parts
-  CRUD for Customers
-  Full CRUD for Service Tickets (with soft delete)
-  Nested relationships in Service Tickets (customers, employees, parts, services)
-  Automatic cost calculation with tax
-  Password hashing for employees
-  Field validations and error handling

## Tech Stack

- Python
- Flask
- SQLAlchemy
- Marshmallow
- SQLite (default for testing)

## Setup

```bash
git clone https://github.com/VELIFZ/mechanicshop-api.git
cd mechanic_shop
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
python app.py