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
-  CI/CD pipeline with GitHub Actions
-  Production deployment on Render


## Tech Stack

- Python
- Flask
- SQLAlchemy (ORM)
- Marshmallow (Serialization)
- PostgreSQL (Production) / SQLite (Development)
- Flask-Migrate (Database migrations)
- Flask-CORS (Cross-origin support)
- Flask-Swagger (API documentation)
- Flask-Limiter (Rate limiting)
- Flask-Caching (Response caching)
- Gunicorn (WSGI server for production)

## Setup

### Local Development

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

### Production Deployment

The application is deployed on Render with automatic deployments via GitHub Actions.

**Live API:** https://mechanic-shop-api-ahv0.onrender.com

**API Documentation:** https://mechanic-shop-api-ahv0.onrender.com/api/docs

## Environment Variables

The application uses environment variables for configuration. Create a `.env` file with the following variables:

### Development
- `SECRET_KEY`: Used for token generation and security
- `DEV_DATABASE_URI`: Database URI for development (default: sqlite:///app.db)
- `TEST_DATABASE_URI`: Database URI for testing (default: sqlite:///test.db)
- `FLASK_ENV`: Set to "development" for local development

### Production
- `SECRET_KEY`: Secure secret key for production
- `DATABASE_URI`: PostgreSQL database URI for production
- `FLASK_ENV`: Set to "production"

For production deployment, make sure to set secure values for all environment variables in your hosting platform.

## CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/main.yaml`) that:

1. **Build**: Sets up Python environment and installs dependencies
2. **Test**: Runs the test suite to ensure code quality
3. **Deploy**: Automatically deploys to Render when tests pass

### Required GitHub Secrets

For the CI/CD pipeline to work, set these secrets in your GitHub repository:
- `SERVICE_ID`: Your Render service ID
- `RENDER_API_KEY`: Your Render API key

## Testing

The project includes comprehensive test suites for all major components:

```bash
# Run all tests
python -m unittest discover tests

# Run specific test files
python -m unittest tests/test_employee.py
python -m unittest tests/test_customer.py
python -m unittest tests/test_ticket.py
python -m unittest tests/test_inventory.py
python -m unittest tests/test_service.py
```

## API Reference

### Base URL
- **Development:** `http://localhost:5001`
- **Production:** `https://mechanic-shop-api-ahv0.onrender.com`

### API Documentation
Interactive API documentation is available at:
- **Development:** `http://localhost:5001/api/docs`
- **Production:** `https://mechanic-shop-api-ahv0.onrender.com/api/docs`

### Authentication
Most endpoints require authentication via JWT token:
1. Login via `/customers/login` or `/employees/login` to receive a token
2. Include the token in subsequent requests:
   ```
   Authorization: Bearer <your_token>
   ```

### Endpoints

#### Customer Authentication
- `POST /customers/login` - Customer login and get access token
- `POST /customers` - Register new customer

#### Employee Authentication  
- `POST /employees/login` - Employee login and get access token

#### Employees
- `GET /employees` - List all employees
- `GET /employees/<id>` - Get employee details
- `POST /employees` - Create new employee
- `PUT /employees/<id>` - Update employee
- `DELETE /employees/<id>` - Delete employee

#### Customers
- `GET /customers/me` - Get current customer profile
- `GET /customers/me/tickets` - Get current customer's tickets
- `GET /employees/customers` - List all customers (employee access)
- `GET /employees/customers/<id>` - Get customer details (employee access)

#### Services
- `GET /services` - List all services
- `GET /services/<id>` - Get service details
- `POST /services` - Create new service
- `PUT /services/<id>` - Update service
- `DELETE /services/<id>` - Delete service

#### Inventory
- `GET /inventory` - List all inventory items
- `GET /inventory/<id>` - Get inventory item details
- `POST /inventory` - Create new inventory item
- `PUT /inventory/<id>` - Update inventory item
- `DELETE /inventory/<id>` - Delete inventory item

#### Service Tickets
- `GET /service-tickets` - List all service tickets
- `GET /service-tickets/<id>` - Get ticket details
- `POST /service-tickets` - Create new ticket
- `PUT /service-tickets/<id>` - Update ticket
- `DELETE /service-tickets/<id>` - Soft delete ticket

For detailed request/response formats, see the interactive API documentation.
