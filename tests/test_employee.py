import unittest
import uuid
from application import create_app
from application.models import db, Employee
from application.utils.utils import hash_password

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
        
        # Get auth token
        response = self.client.post('/employees/login', json={
            'email': self.test_email,
            'password': self.test_password
        })
        
        # Check if login was successful
        self.assertEqual(response.status_code, 200, 
                         f"Login failed with response: {response.get_json()}")
        
        data = response.get_json()
        self.token = data['token']
        self.headers = {'Authorization': f'Bearer {self.token}'}
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        super().tearDown()
    
    # 1- valid creation
    def test_create_valid_employee(self):
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "password": "Password123",
            "salary": 50000.00,
            "role": "mechanic"
        }
    
        response = self.client.post('/employees/', json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["email"], "john@example.com")
        self.assertNotIn("password", data)
        
    # 2- invalid creation
    def test_create_invalid_employee(self):
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "password": "Password123",
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
            "email": self.test_email,  # Use the same email created in setUp
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

        
    # 5- Fetch all
    def test_get_all_employees(self):
        response = self.client.get('/employees/', headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        
        emails = [emp["email"] for emp in data]
        self.assertIn(self.test_email, emails)  
        
    # 6- Single fetch by id
    def test_get_employee_by_id(self):
        response = self.client.get(f'/employees/{self.employee_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data["id"], self.employee_id)
        self.assertEqual(data["email"], self.test_email)
        
    # 7- get non-exit employee
    def test_get_nonexistent_employee(self):
        response = self.client.get('/employees/8888', headers=self.headers)
        self.assertEqual(response.status_code, 404)
        
        data = response.get_json()
        self.assertEqual(data["message"], "Employee not found")
        
    # 8- full update
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

        data = response.get_json()
        self.assertEqual(data["name"], "Updated Name")
        self.assertEqual(data["email"], "updated@test.com")

    # 9- invalid update
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

    # 10- partial valid update
    def test_patch_employee(self):
        payload = {
            "phone": "9998887777",
            "role": "manager"
        }

        response = self.client.patch(f'/employees/{self.employee_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["phone"], "9998887777")
        self.assertEqual(data["role"], "manager")

    # 11- delete by id
    def test_delete_employee(self):
        response = self.client.delete(f'/employees/{self.employee_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["message"], "Employee deleted successfully")

        # Confirm it no longer exists
        check = self.client.get(f'/employees/{self.employee_id}', headers=self.headers)
        self.assertEqual(check.status_code, 404)

    # 12- delete non-exist employee
    def test_delete_nonexistent_employee(self):
        response = self.client.delete('/employees/344', headers=self.headers)
        self.assertEqual(response.status_code, 404)

        data = response.get_json()
        self.assertEqual(data["message"], "Employee not found")
    
    def test_get_mechanics_by_ticket_count(self):
        # Create test mechanics
        mechanic1 = Employee(
            name="Test Mechanic 1", 
            email="mechanic1@test.com", 
            phone="1234567891", 
            password="Password123", 
            salary=55000.00, 
            role="mechanic"
        )
        mechanic2 = Employee(
            name="Test Mechanic 2", 
            email="mechanic2@test.com", 
            phone="1234567892", 
            password="Password123", 
            salary=60000.00, 
            role="mechanic"
        )
        
        db.session.add_all([mechanic1, mechanic2])
        db.session.commit()
        
        # Create test customer
        from application.models import Customer
        customer = Customer(
            name="Test Customer",
            email="testcustomer@test.com",
            phone="1234567890",
            password="Password123"
        )
        db.session.add(customer)
        db.session.commit()
        
        # Create test tickets with different mechanics
        from application.models import ServiceTicket
        ticket1 = ServiceTicket(
            vin="TEST1234567890A",
            work_summary="Test work 1",
            cost=100.0,
            status="closed",
            customer_id=customer.id
        )
        ticket2 = ServiceTicket(
            vin="TEST1234567890B",
            work_summary="Test work 2",
            cost=150.0,
            status="closed",
            customer_id=customer.id
        )
        ticket3 = ServiceTicket(
            vin="TEST1234567890C",
            work_summary="Test work 3",
            cost=200.0,
            status="closed",
            customer_id=customer.id
        )
        
        db.session.add_all([ticket1, ticket2, ticket3])
        db.session.commit()
        
        # Assign mechanics to tickets (mechanic1 gets 2, mechanic2 gets 1)
        ticket1.employees.append(mechanic1)
        ticket2.employees.append(mechanic1)
        ticket3.employees.append(mechanic2)
        db.session.commit()
        
        # Call the endpoint and check results
        response = self.client.get('/employees/by-ticket-count')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)  # Should have 2 mechanics
        
        # The first mechanic should be mechanic1 (with 2 tickets)
        self.assertEqual(data[0]["id"], mechanic1.id)
        self.assertEqual(data[0]["ticket_count"], 2)
        
        # The second mechanic should be mechanic2 (with 1 ticket)
        self.assertEqual(data[1]["id"], mechanic2.id)
        self.assertEqual(data[1]["ticket_count"], 1)
 