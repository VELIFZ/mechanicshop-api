# Mechanic Shop API

A basic service ticket system for auto mechanic shop with customers, mechanics, parts, and services. Built with Flask, SQLAlchemy, and Marshmallow.

## Features

-  CRUD for Employees (mechanics and staff)
-  CRUD for Services (types of auto services offered)
-  CRUD for Inventory & Serialized Parts (tracking individual parts by serial number)
-  CRUD for Customers
-  Full CRUD for Service Tickets (with soft delete)
-  Nested relationships in Service Tickets (customers, employees, parts, services)
-  Automatic cost calculation with tax
-  Password hashing for employees
-  Field validations and error handling
-  Rate limiting and caching


## Tech Stack

- Python
- Flask
- SQLAlchemy (ORM)
- Marshmallow (Serialization)
- SQLite (default for testing)
- Flask-Migrate (Database migrations)
- Flask-CORS (Cross-origin support)

## Setup

```bash
git clone https://github.com/VELIFZ/mechanicshop-api.git
cd mechanic_shop
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create a .env file with configuration (see Environment Variables section)
touch .env  # Create empty .env file
# Edit .env file with your configuration

flask db init  # If migrations directory doesn't exist
flask db migrate -m "Initial migration"
flask db upgrade
python app.py
```

## Environment Variables

The application uses environment variables for configuration. Copy the `env.example` file to `.env` and update the values:

- `SECRET_KEY`: Used for token generation and security
- `DEV_DATABASE_URI`: Database URI for development
- `TEST_DATABASE_URI`: Database URI for testing
- `DATABASE_URI`: Database URI for production

For production deployment, make sure to set secure values for all environment variables.
