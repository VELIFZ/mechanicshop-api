import unittest
from application import create_app
from application.models import db, Employee

class TestEmployee(unittest.TestCase):
    
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        self.employee = Employee(name = 'mechanic test', email = 'test@test.com', phone = '1233456789', password='test', salary = "12000.00", role = 'techician')
       
        db.session.add(self.employee)
        db.session.commit()
        self.employee_id = self.employee.id
    
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
            "password": "secure123",
            "salary": 50000.00,
            "role": "mechanic"
        }
    
        response = self.client.post('/employees/', json = payload)
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
            "password": "secure123",
        }   
        response = self.client.post('/employees/', json = payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        #print(f"data messah=ge : {data} ") # {'errors': {'role': ['Missing data for required field.'], 'salary': ['Missing data for required field.']}, 'message': 'Invalid input'}
        self.assertIn("errors", data)
        self.assertIn("salary", data["errors"])
        self.assertIn("role", data["errors"])
        # Check error message text
        self.assertEqual(data["errors"]["salary"][0], "Missing data for required field.")
    
    # 3- create dublicate email
    def test_create_employee_duplicate_email(self):
        payload = {
            "name": "John Doe",
            "email": "test@test.com",
            "phone": "1234567890",
            "password": "secure123",
            "salary": 50000.00,
            "role": "mechanic"
        }
        
        response = self.client.post('/employees/', json=payload)
        self.assertEqual(response.status_code, 409)

        data = response.get_json()
        self.assertEqual(data["message"], "Employee already exists")
        self.assertIn("employee", data)
        self.assertEqual(data["employee"]["email"], "test@test.com")
        
    # 4- wrong email format
    def test_create_employee_invalid_email(self):
        payload = {
            "name": "Invalid Email User",
            "email": "not-an-email",  # invalid format
            "phone": "1234567890",
            "password": "pass123",
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
        response = self.client.get('/employees/')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        
        emails = [emp["email"] for emp in data]
        self.assertIn("test@test.com", emails)  
        
    # 6- Single fetch by id
    def test_get_employee_by_id(self):
        response = self.client.get(f'/employees/{self.employee_id}')
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data["id"], self.employee_id)
        self.assertEqual(data["email"], "test@test.com")
        
    # 7- get non-exit employee
    def test_get_nonexistent_employee(self):
        response = self.client.get('/employees/8888')
        self.assertEqual(response.status_code, 404)
        
        data = response.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Employee not found")
        
    # 8- full update
    def test_update_employee(self):
        payload = {
            "name": "Updated Name",
            "email": "updated@test.com",
            "phone": "1112223333",
            "password": "newpass",
            "salary": 15000.00,
            "role": "supervisor"
        }

        response = self.client.put(f'/employees/{self.employee_id}', json=payload)
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
            "password": "newpass",
            "salary": 15000.00,
        }

        response = self.client.put(f'/employees/{self.employee_id}', json=payload)
        self.assertEqual(response.status_code, 400)

        self.assertIn("errors", response.get_json())

    # 10- partial valid update
    def test_patch_employee(self):
        payload = {
            "phone": "9998887777",
            "role": "manager"
        }

        response = self.client.patch(f'/employees/{self.employee_id}', json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["phone"], "9998887777")
        self.assertEqual(data["role"], "manager")

    # 11- delete by id
    def test_delete_employee(self):
        response = self.client.delete(f'/employees/{self.employee_id}')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["message"], "Employee deleted successfully")

        # Confirm it no longer exists
        check = self.client.get(f'/employees/{self.employee_id}')
        self.assertEqual(check.status_code, 404)

    # 12- delete non-exist employee
    def test_delete_nonexistent_employee(self):
        response = self.client.delete('/employees/344')
        self.assertEqual(response.status_code, 404)

        data = response.get_json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Employee not found")
