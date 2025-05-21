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

## Testing

The project includes comprehensive test suites for all major components:

```bash
# Run all tests
python -m pytest

# Run specific test files
python -m pytest tests/test_employee.py
python -m pytest tests/test_customer.py
python -m pytest tests/test_ticket.py
python -m pytest tests/test_inventory.py
python -m pytest tests/test_service_.py

```

## API Reference

### Base URL
When running locally: `http://localhost:5000/api/v1`

### API Documentation
Interactive API documentation is available at: `http://127.0.0.1:5000/api/docs/`

### Authentication
Most endpoints require authentication via JWT token:
1. Login via `/api/v1/auth/login` to receive a token
2. Include the token in subsequent requests:
   ```
   Authorization: Bearer <your_token>
   ```

### Endpoints

#### Authentication
- `POST /api/v1/auth/login` - Login and get access token
- `POST /api/v1/auth/refresh` - Refresh access token

#### Employees
- `GET /api/v1/employees` - List all employees
- `GET /api/v1/employees/<id>` - Get employee details
- `POST /api/v1/employees` - Create new employee
- `PUT /api/v1/employees/<id>` - Update employee
- `DELETE /api/v1/employees/<id>` - Delete employee

#### Customers
- `GET /api/v1/customers` - List all customers
- `GET /api/v1/customers/<id>` - Get customer details
- `POST /api/v1/customers` - Create new customer
- `PUT /api/v1/customers/<id>` - Update customer
- `DELETE /api/v1/customers/<id>` - Delete customer

#### Services
- `GET /api/v1/services` - List all services
- `GET /api/v1/services/<id>` - Get service details
- `POST /api/v1/services` - Create new service
- `PUT /api/v1/services/<id>` - Update service
- `DELETE /api/v1/services/<id>` - Delete service

#### Inventory
- `GET /api/v1/inventory` - List all inventory items
- `GET /api/v1/inventory/<id>` - Get inventory item details
- `POST /api/v1/inventory` - Create new inventory item
- `PUT /api/v1/inventory/<id>` - Update inventory item
- `DELETE /api/v1/inventory/<id>` - Delete inventory item

#### Service Tickets
- `GET /api/v1/tickets` - List all service tickets
- `GET /api/v1/tickets/<id>` - Get ticket details
- `POST /api/v1/tickets` - Create new ticket
- `PUT /api/v1/tickets/<id>` - Update ticket
- `DELETE /api/v1/tickets/<id>` - Soft delete ticket

For detailed request/response formats, see the API documentation comments in the route handler files.
