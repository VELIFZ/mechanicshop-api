import unittest
import uuid
from application import create_app
from application.models import db, Employee, ServiceTicket, Customer
from application.utils.utils import hash_password

STRONG_TEST_PASSWORD = "ValidTest123"

class TestEmployee(unittest.TestCase):
    
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Generate unique email to avoid unique constraint violations
        unique_id = str(uuid.uuid4())[:8]
        self.test_email = f'test_{unique_id}@test.com'
        self.test_password = 'Password123'
        
        # Hash the password before storing it
        hashed_password = hash_password(self.test_password)
        self.employee = Employee(
            name='mechanic test', 
            email=self.test_email, 
            phone='1234567890', 
            password=hashed_password, 
            salary="12000.00", 
            role='techician'
        )
       
        db.session.add(self.employee)
        db.session.commit()
        self.employee_id = self.employee.id
        
        self.customer = Customer(
            name='Test Customer',
            email='testcustomer@test.com',
            phone='1234567890',
            password=hash_password('customerpassword')
        )
        db.session.add(self.customer)
        db.session.commit()
        self.customer_id = self.customer.id
        
        # Get auth token
        response = self.client.post('/employees/login', json={
            'email': self.test_email,
            'password': self.test_password
        })
        
        # Check if login was successful
        self.assertEqual(response.status_code, 200, 
                         f"Login failed with response: {response.get_json()}")
        
        data = response.get_json()
        self.token = data['data']['token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        
    # ------- MARK: Login Tests -------
    # login fails with invalid credentials
    def test_login_invalid_credentials(self):
        payload = {
            "email": "wrongemail@test.com",
            "password": "wrongpassword"
        }
        response = self.client.post('/employees/login', json=payload)
        self.assertEqual(response.status_code, 401)
        
        data = response.get_json()
        self.assertEqual(data["message"], "Invalid email or password")
        
    # edge test
    def test_deleted_employee_cannot_login(self):
        # delete employee
        self.client.delete(f'/employees/{self.employee_id}', headers=self.headers)

        # login try
        response = self.client.post('/employees/login', json={
            'email': self.test_email,
            'password': self.test_password
        })
        self.assertEqual(response.status_code, 401)

        data = response.get_json()
        self.assertEqual(data["message"], "Invalid email or password")

    # ------- MARK: Create Tests -------
    # 1- valid creation
    def test_create_valid_employee(self):
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "password": STRONG_TEST_PASSWORD,
            "salary": 50000.00,
            "role": "mechanic"
        }
    
        response = self.client.post('/employees/', json=payload)
        self.assertEqual(response.status_code, 201)
        
        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertEqual(data["email"], "john@example.com")
        self.assertNotIn("password", data)
        
    # 2- invalid creation
    def test_create_invalid_employee(self):
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "password": STRONG_TEST_PASSWORD
        }   
        response = self.client.post('/employees/', json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("errors", data)
        self.assertIn("salary", data["errors"])
        self.assertIn("role", data["errors"])
       
        self.assertEqual(data["errors"]["salary"][0], "Missing data for required field.")
    
    # 3- create dublicate email
    def test_create_employee_duplicate_email(self):
        payload = {
            "name": "John Doe",
            "email": self.test_email,  #same email created in setUp
            "phone": "1234567890",
            "password": "Password123",
            "salary": 50000.00,
            "role": "mechanic"
        }
        
        response = self.client.post('/employees/', json=payload)
        self.assertEqual(response.status_code, 409)

        data = response.get_json()
        self.assertEqual(data["message"], "Employee already exists")
        self.assertIn("employee", data["details"])
        self.assertEqual(data["details"]["employee"]["email"], self.test_email)
        
    # 4- wrong email format
    def test_create_employee_invalid_email(self):
        payload = {
            "name": "Invalid Email User",
            "email": "not-an-email",  
            "phone": "1234567890",
            "password": "Password123",
            "salary": 10000.00,
            "role": "mechanic"
        }

        response = self.client.post('/employees/', json=payload)
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn("errors", data)
        self.assertIn("email", data["errors"])

    # ------- Get Tests -------
    # 1- Fetch all
    def test_get_all_employees(self):
        response = self.client.get('/employees/', headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        
        emails = [emp["email"] for emp in data]
        self.assertIn(self.test_email, emails)  
        
    # 2- Single fetch by id
    def test_get_employee_by_id(self):
        response = self.client.get(f'/employees/{self.employee_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertEqual(data["id"], self.employee_id)
        self.assertEqual(data["email"], self.test_email)
        
    # 3- Get all customers
    def test_get__customers(self):
        headers = self.headers
        response = self.client.get('/employees/customers', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        self.assertIn('data', response_data)
        self.assertGreater(len(response_data['data']), 0)
        self.assertIn('email', response_data['data'][0])
        
    # 4- Get single customer (authenticated route)
    def test_get__single_customer(self):
        # Get authorization token
        headers = self.headers
        response = self.client.get(f'/employees/customers/{self.customer_id}', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()['data']
        self.assertEqual(data['name'], 'Test Customer')
        self.assertEqual(data['email'], 'testcustomer@test.com')
        
    # 5- get non-exit employee
    def test_get_nonexistent_employee(self):
        response = self.client.get('/employees/8888', headers=self.headers)
        self.assertEqual(response.status_code, 404)
        
        data = response.get_json()
        self.assertEqual(data["message"], "Employee not found")
        
    # 6- get mechanics by ticket count
    def test_get_mechanics_by_ticket_count(self):
        # Create test mechanics
        mechanic1 = Employee(
            name="Test Mechanic 1", 
            email="mechanic1@test.com", 
            phone="1111111111", 
            password="Password123", 
            salary=50000, 
            role="mechanic"
        )
        mechanic2 = Employee(
            name="Test Mechanic 2", 
            email="mechanic2@test.com", 
            phone="2222222222", 
            password="Password123", 
            salary=55000, 
            role="mechanic"
        )
        db.session.add_all([mechanic1, mechanic2])
        db.session.commit()
        
        # Create test tickets with different mechanics
        ticket1 = ServiceTicket(
            vin="TESTMECH1000",
            work_summary="Test for ticket count",
            status="open",
            customer_id=1,
            cost=100.0
        )
        ticket2 = ServiceTicket(
            vin="TESTMECH2000",
            work_summary="Test for ticket count 2",
            status="open",
            customer_id=1,
            cost=150.0
        )
        ticket3 = ServiceTicket(
            vin="TESTMECH3000",
            work_summary="Test for ticket count 3",
            status="open",
            customer_id=1,
            cost=200.0
        )
        
        db.session.add_all([ticket1, ticket2, ticket3])
        db.session.commit()
        
        # mechanic1 with 2 tickets, mechanic2 with 1
        ticket1.employees.append(mechanic1)
        ticket2.employees.append(mechanic1)
        ticket3.employees.append(mechanic2)
        db.session.commit()
        
        # Get the API response
        response = self.client.get('/employees/by-ticket-count', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertIsInstance(data, list)
        
        # Checking that mechanics are ordered by ticket count
        self.assertEqual(data[0]["ticket_count"], 2)
        self.assertEqual(data[0]["name"], "Test Mechanic 1")
        self.assertEqual(data[1]["ticket_count"], 1)
        self.assertEqual(data[1]["name"], "Test Mechanic 2")
        
    # ------- Update Tests -------
    # 1- full update
    def test_update_employee(self):
        payload = {
            "name": "Updated Name",
            "email": "updated@test.com",
            "phone": "1112223333",
            "password": "Password123",
            "salary": 15000.00,
            "role": "supervisor"
        }

        response = self.client.put(f'/employees/{self.employee_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertEqual(data["name"], "Updated Name")
        self.assertEqual(data["email"], "updated@test.com")

    # 2- invalid update
    def test_update_employee_invalid(self):
        payload = {
            "name": "",
            "email": "updated@test.com",
            "phone": "1112223333",
            "password": "Password123",
            "salary": 15000.00,
        }

        response = self.client.put(f'/employees/{self.employee_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)

        self.assertIn("errors", response.get_json())
    
    # ------- Patch Tests -------
    # 1- Patch endpoint allows any field; patching + checking more just in case if business needs it
    def test_patch_employee(self):
        payload = {
            "phone": "2223334455"
        }
        response = self.client.patch(f'/employees/{self.employee_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        
        # response check
        data = response.get_json()["data"]
        self.assertEqual(data["phone"], "2223334455")
        
        # additional db fetch check
        with self.app.app_context():
            updated_employee = db.session.get(Employee, self.employee_id)
            self.assertEqual(updated_employee.phone, "2223334455")
        
    # 2- patch a customer by employee 
    def test_patch_customer_as_employee(self):
        payload = {
            "phone": "9876543210",
            "name": "Updated Customer Name"
        }
        response = self.client.patch(f'/employees/customers/{self.customer_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()["data"]
        self.assertEqual(data["phone"], "9876543210")
        self.assertEqual(data["name"], "Updated Customer Name")

        # Confirm in DB
        with self.app.app_context():
            updated_customer = db.session.get(Customer, self.customer_id)
            self.assertEqual(updated_customer.phone, "9876543210")
            self.assertEqual(updated_customer.name, "Updated Customer Name")
            
    # ------- Delete Tests -------
    # 1- delete by id
    def test_delete_employee(self):
        response = self.client.delete(f'/employees/{self.employee_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["message"], "Employee deleted successfully")

        # Confirm it no longer exists
        check = self.client.get(f'/employees/{self.employee_id}', headers=self.headers)
        self.assertEqual(check.status_code, 404)

    # 2- delete non-exist employee
    def test_delete_nonexistent_employee(self):
        response = self.client.delete('/employees/344', headers=self.headers)
        self.assertEqual(response.status_code, 404)

        data = response.get_json()
        self.assertEqual(data["message"], "Employee not found")

