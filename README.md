# Mechanic Shop API

A comprehensive RESTful Flask API for managing mechanic shop operations. Built with modern technologies including Flask 3.x, SQLAlchemy 2.0, PostgreSQL, Redis, and Docker with production-ready features.

## Features

### Core Functionality
- **Full CRUD Operations** for all entities:
  - **Employees** (mechanics, managers, admins) with role-based access
  - **Customers** with authentication and profile management  
  - **Services** (oil change, brake repair, etc.) with pricing
  - **Inventory & Serialized Parts** with stock tracking by serial numbers
  - **Service Tickets** with comprehensive workflow management

### Advanced Features
- **Soft Delete** for service tickets and inventory items
- **Serialized Parts Tracking** with unique serial numbers and status management
- **Automatic Cost Calculation** with 8% tax rate on closed tickets
- **Complex Relationships** with many-to-many associations between:
  - Employees ↔ Service Tickets (multiple mechanics per ticket)
  - Services ↔ Service Tickets (multiple services per ticket)
  - Serialized Parts ↔ Service Tickets (parts usage tracking)

### Security & Performance
- **JWT Authentication** with role-based access control (customer/employee)
- **Password Security** with bcrypt hashing and strength validation
- **Rate Limiting** via Redis (200/day, 50/hour per IP)
- **Response Caching** with Redis backend
- **Input Validation** with comprehensive Marshmallow schemas
- **CORS Support** for cross-origin requests

### API & Documentation
- **Interactive Swagger UI** at `/api/docs`
- **Comprehensive API Documentation** with examples
- **Pagination Support** for all list endpoints
- **Advanced Filtering** by status, role, customer, etc.
- **Structured Error Responses** with detailed validation messages

### DevOps & Production
- **Multi-stage Dockerized** deployment with optimization
- **Docker Compose** orchestration with PostgreSQL and Redis
- **CI/CD Pipeline** with GitHub Actions (build → test → deploy)
- **Production-ready** with Gunicorn WSGI server
- **Health Checks** and monitoring support
- **Database Migrations** with Flask-Migrate

## 🛠 Tech Stack

- **Backend Framework**: Flask 3.1.0
- **Database ORM**: SQLAlchemy 2.0.40 with declarative mapping
- **Schema Validation**: Marshmallow 3.26.1 with SQLAlchemy integration
- **Database**: 
  - PostgreSQL 15 (Production)
  - SQLite (Development/Testing)
- **Authentication**: PyJWT 2.10.1 with bcrypt password hashing
- **Caching & Rate Limiting**: Redis 5.0.1 with Flask-Limiter
- **API Documentation**: Swagger UI (flask-swagger-ui 4.11.1)
- **Production Server**: Gunicorn 23.0.0 
- **Containerization**: Docker with multi-stage builds
- **CI/CD**: GitHub Actions with Render deployment
- **Additional**: Flask-CORS, Flask-Compress, Flask-Migrate

## Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for production setup)
- PostgreSQL (for production)
- Redis (for rate limiting & caching)

### Local Development

```bash
# Clone the repository
git clone https://github.com/VELIFZ/mechanicshop-api.git
cd mechanic_shop

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (see Environment Variables section)
cp .env.example .env  # Create .env file
# Edit .env with your configuration

# Initialize database
flask db init  # If migrations directory doesn't exist
flask db migrate -m "Initial migration"
flask db upgrade

# Run the development server
python app.py
```

The API will be available at `http://localhost:5001`

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# API available at http://localhost:5002
# PostgreSQL at localhost:5433
# Redis at localhost:6379
```

### Production Deployment

The application includes a complete CI/CD pipeline and can be deployed to platforms like Render, Fly.io, or any Docker-compatible hosting service.

**Live Demo**: https://mechanic-shop-api-ahv0.onrender.com
**API Docs**: https://mechanic-shop-api-ahv0.onrender.com/api/docs

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Security
SECRET_KEY=your-super-secret-key-here

# Database Configuration
# Development (SQLite)
DEV_DATABASE_URI=sqlite:///app.db
TEST_DATABASE_URI=sqlite:///test.db

# Production (PostgreSQL) 
DATABASE_URI=postgresql://user:password@host:port/database

# Redis (for rate limiting and caching)
REDIS_URL=redis://localhost:6379

# Application Environment
FLASK_ENV=development  # development, production, testing
```

### Configuration Classes

The app uses environment-specific configurations:

- **DevelopmentConfig**: SQLite database, 24-hour JWT tokens, debug mode
- **ProductionConfig**: PostgreSQL database, 1-hour JWT tokens, optimized settings
- **TestingConfig**: In-memory SQLite, 5-minute JWT tokens, testing mode

## Testing

The project includes comprehensive test coverage using Python's built-in `unittest` module:

```bash
# Run all tests
python -m unittest discover tests

# Run specific test modules
python -m unittest tests.test_employee
python -m unittest tests.test_customer  
python -m unittest tests.test_ticket
python -m unittest tests.test_inventory
python -m unittest tests.test_service_

# Run with verbose output
python -m unittest discover tests -v
```

### Test Coverage
- **Employee Management**: Authentication, CRUD operations, role validation
- **Customer Management**: Registration, profile management, ticket access
- **Service Tickets**: Creation, updates, status management, cost calculation
- **Inventory & Parts**: Stock management, serialized part tracking
- **Services**: Service type management and pricing
- **Authentication**: JWT token generation, validation, role-based access

## 🔗 API Reference

### Base URLs
- **Development**: `http://localhost:5001`
- **Docker**: `http://localhost:5002` 
- **Production**: `https://mechanic-shop-api-ahv0.onrender.com`

### Interactive Documentation
- **Development**: `http://localhost:5001/api/docs`
- **Production**: `https://mechanic-shop-api-ahv0.onrender.com/api/docs`

### Authentication

Most endpoints require JWT authentication:

1. **Login** via `/customers/login` or `/employees/login`
2. **Include token** in subsequent requests:
   ```
   Authorization: Bearer <your_jwt_token>
   ```

### Key Endpoints

#### Authentication
```
POST /customers/login          # Customer authentication
POST /customers               # Customer registration  
POST /employees/login         # Employee authentication
```

#### Employee Management (Employee Access Required)
```
GET    /employees                    # List all employees
POST   /employees                    # Create employee
GET    /employees/{id}               # Get employee details
PUT    /employees/{id}               # Update employee
DELETE /employees/{id}               # Delete employee
GET    /employees/by-ticket-count    # Get mechanics by workload
GET    /employees/me                 # Get current employee profile
GET    /employees/me/tickets         # Get assigned tickets
```

#### Customer Management
```
GET    /customers/me                 # Get customer profile (customer)
PATCH  /customers/{id}               # Update customer (customer)
GET    /customers/me/tickets         # Get customer's tickets (customer)
PATCH  /customers/me/update-password # Change password (customer)
GET    /employees/customers          # List customers (employee)
GET    /employees/customers/{id}     # Get customer details (employee)
PATCH  /employees/customers/{id}     # Update customer (employee)
```

#### Service Ticket Management (Employee Access Required)
```
GET    /service-tickets             # List all tickets (with pagination/filtering)
POST   /service-tickets             # Create new ticket
GET    /service-tickets/{id}        # Get ticket details
PATCH  /service-tickets/{id}        # Update ticket
DELETE /service-tickets/{id}        # Soft delete ticket
```

#### Services Management (Employee Access Required)
```
GET    /services                    # List all services
POST   /services                    # Create service
GET    /services/{id}               # Get service details
PUT    /services/{id}               # Update service
PATCH  /services/{id}               # Partial update service
DELETE /services/{id}               # Delete service
```

#### Inventory Management (Employee Access Required)
```
GET    /inventory                   # List inventory items
POST   /inventory                   # Create inventory item
GET    /inventory/{id}              # Get inventory details
PUT    /inventory/{id}              # Update inventory
PATCH  /inventory/{id}              # Partial update inventory
DELETE /inventory/{id}              # Soft delete inventory
```

### Query Parameters

Most list endpoints support:
- `page` (default: 1)
- `limit` (default: 10) 
- `sort_by` (field name)
- `sort_order` (asc/desc)
- `status` (for tickets: open/in_progress/closed)
- `search` (text search)

Example: `/service-tickets?page=2&limit=5&status=open&sort_by=created_at&sort_order=desc`

##  Architecture

### Database Schema

The application uses a normalized relational database with the following key relationships:

- **Customer** → **ServiceTicket** (1:Many)
- **Employee** ↔ **ServiceTicket** (Many:Many) 
- **Service** ↔ **ServiceTicket** (Many:Many)
- **Inventory** → **SerializedPart** (1:Many)
- **SerializedPart** ↔ **ServiceTicket** (Many:Many)

### Key Business Logic

- **Cost Calculation**: Automatic calculation of service ticket costs with 8% tax
- **Parts Management**: Serialized parts can only be used once per ticket
- **Status Workflow**: Service tickets follow open → in_progress → closed workflow
- **Soft Deletes**: Tickets and inventory use soft deletes for data integrity
- **Role-based Access**: Customers can only access their own data, employees have broader access

## CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/main.yaml`) with three stages:

1. **Build**: Environment setup and dependency installation
2. **Test**: Complete test suite execution
3. **Deploy**: Automatic deployment to Render on successful tests

### Required Secrets

Configure these in your GitHub repository settings:
- `SERVICE_ID`: Your Render service ID
- `RENDER_API_KEY`: Your Render API key

## API Response Format

All API responses follow a consistent structure:

### Success Response
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": { /* response data */ },
  "meta": { /* pagination, etc. */ }
}
```

### Error Response  
```json
{
  "status": "error", 
  "message": "Error description",
  "details": { /* additional error details */ },
  "errors": { /* validation errors */ }
}
```

## Security Features

- **JWT Authentication** with configurable expiration times
- **Password Hashing** using bcrypt with salt
- **Password Strength Validation** (minimum 8 characters, letters + numbers)
- **Rate Limiting** to prevent abuse (200/day, 50/hour per IP)
- **Input Validation** with Marshmallow schemas
- **SQL Injection Protection** via SQLAlchemy ORM
- **CORS Configuration** for secure cross-origin requests

## Performance Features

- **Response Caching** with Redis backend
- **Database Connection Pooling** via SQLAlchemy
- **Pagination** for large result sets
- **Lazy Loading** for database relationships
- **Multi-stage Docker Builds** for optimized container size
- **Gunicorn Workers** for concurrent request handling

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
