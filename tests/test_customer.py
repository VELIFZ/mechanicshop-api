import unittest
from application.utils.utils import hash_password
from application import create_app
from application.models import db, Customer, ServiceTicket
import jwt
from flask import current_app

class TestCustomer(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.customer = Customer(name="Test Customer", email="test@test.com", phone="0000000000", password=hash_password("test1234") )
            db.session.add(self.customer)
            db.session.commit()
            self.customer_id = self.customer.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        return super().tearDown()
    
    # Helper method for authentication
    def login_and_get_token(self):
        login_payload = {"email": "test@test.com", "password": "test1234"}
        login_response = self.client.post("/customers/login", json=login_payload)
        token = login_response.get_json()["data"]["token"]
        return {"Authorization": f"Bearer {token}"}
    
    # -----POST-----
    # 1- Valid creation
    def test_create__customer(self):
        payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "1234567890",
            "password": 'test1234'
        }
        response = self.client.post('/customers/', json=payload)
        self.assertEqual(response.status_code, 201)
        
        data = response.get_json()
        # Check if got back valid data
        self.assertEqual(data["data"]["name"], "Jane Doe")
        
    # 2- invalid creation    
    def test_create__invalid_customer(self):
        payload = {
            "name": "John Doe",
            "phone": "1234567891"
        }

        response = self.client.post('/customers/', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('errors', response.json)
        self.assertIn('email', response.json['errors'])

    # 3- Duplicate email on create
    def test_unique_email(self):
        payload = {
            "name": "John Doe",
            "phone": "1234567891",
            "email": "TEST@test.com", # dub email
            "password": 'test1234'
        }

        response = self.client.post('/customers/', json=payload)
        # This route returns 200 if customer already exists
        self.assertEqual(response.status_code, 409)
        
        data = response.get_json()

        # Check the message and returned existing customer
        self.assertEqual(data["message"], "Customer already exists")
        self.assertIn("customer", data["details"])
        self.assertEqual(data["details"]["customer"]["email"], "test@test.com") # confirms case-insensitive match

    # 4- Invalid email format   
    def test_create__customer_invalid_email_format(self):
        payload = {"name": "Foo", "email": "not-an-email", "phone": "1231231234", "password": 'test1234'}
        response = self.client.post('/customers/', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.get_json()['errors'])
        
    # 5- Login
    def test_valid_login(self):
        payload = {"email": "test@test.com", "password": "test1234"}
        response = self.client.post("/customers/login", json=payload)
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn("token", response_data["data"])
        
    # 6- Token decode direct
    def test_token_decode_direct(self):
        headers = self.login_and_get_token()
        token = headers["Authorization"].split(" ")[1]

        with self.app.app_context():
            decoded = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])

        self.assertIn("sub", decoded)
        self.assertIn("role", decoded)
        self.assertEqual(decoded["role"], "customer")
        self.assertEqual(decoded["sub"], str(self.customer_id))  # sub is a string

    # 7- Invalid password
    def test_invalid_password(self):
        payload = {"email": "test@test.com", "password": "wrongpass"}
        response = self.client.post("/customers/login", json=payload)
        self.assertEqual(response.status_code, 400)    

    # 8- Nonexistent user
    def test_nonexistent_user(self):
        payload = {"email": "nouser@test.com", "password": "any"}
        response = self.client.post("/customers/login", json=payload)
        self.assertEqual(response.status_code, 400)

    # 9- test_phone_length_or_format
    def test_phone_length_or_format(self):
        payload = {"name": "Test Customer", "email": "test@test.com", "phone": "12345678901234567890", "password": "test1234"}
        response = self.client.post("/customers/", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone', response.get_json()['errors'])

    # -----GET-----
    # 1- Get my profile
    def test_get_my_profile(self):
        headers = self.login_and_get_token()
        response = self.client.get("/customers/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["email"], "test@test.com")
        
    # 2- Get all tickets for a customer (authenticated route)
    def test_get_my_all_tickets(self):
        # Create a test ticket first
        with self.app.app_context():
            ticket = ServiceTicket(
                customer_id=self.customer_id,
                vin="TESTTKT12345678",
                work_summary="Test ticket",
                cost=75.00,
                status="open"
            )
            db.session.add(ticket)
            db.session.commit()
        
        # Log in and get token
        headers = self.login_and_get_token()
        
        # Get my tickets
        response = self.client.get('/customers/me/tickets', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIn("data", data)
        self.assertIn("meta", data)
        self.assertIn("pagination", data["meta"])
        self.assertEqual(data["meta"]["pagination"]["total_items"], 1)
        
        # Verify ticket data
        tickets = data["data"]
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["vin"], "TESTTKT12345678")
        self.assertEqual(tickets[0]["work_summary"], "Test ticket")

    # 3- Get tickets with status filter (authenticated route)
    def test_get_my_tickets_with_status_filter(self):
        # Create tickets with different statuses
        with self.app.app_context():
            open_ticket = ServiceTicket(
                customer_id=self.customer_id,
                vin="OPENTKT123456789",
                work_summary="Open ticket",
                cost=80.00,
                status="open"
            )
            
            closed_ticket = ServiceTicket(
                customer_id=self.customer_id,
                vin="CLSDTKT123456789",
                work_summary="Closed ticket",
                cost=90.00,
                status="closed"
            )
            
            db.session.add_all([open_ticket, closed_ticket])
            db.session.commit()
            
        # Get token
        headers = self.login_and_get_token()
        
        # Filter by open status
        response = self.client.get('/customers/me/tickets?status=open', headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIn("data", data)
        tickets = data["data"]
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["status"], "open")
    
    # -----PATCH-----
    # 1- Partial update a customer
    def test_patch_customer(self):
        headers = self.login_and_get_token()
        payload = {"name": "The Customer", "phone": "1231231234"}
        response = self.client.patch(f'/customers/{self.customer_id}', json=payload, headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()["data"]
        self.assertEqual(data["name"], "The Customer")
        self.assertEqual(data["phone"], "1231231234")
        
    # 2- Update password (authenticated route)
    def test_update_password(self):
        # Get token
        headers = self.login_and_get_token()
        
        # Try to update with wrong current password
        response = self.client.patch(
            '/customers/update-password',
            json={"current_password": "wrong", "new_password": "newpass123"},
            headers=headers
        )
        self.assertEqual(response.status_code, 401)
        
        # Update with correct password
        response = self.client.patch(
            '/customers/update-password',
            json={"current_password": "test1234", "new_password": "newpass123"},
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        
        # Try to login with new password
        payload = {"email": "test@test.com", "password": "newpass123"}
        response = self.client.post("/customers/login", json=payload)
        self.assertEqual(response.status_code, 200)
    
    #3 - Not allowed field
    def test_patch_customer_with_not_allowed_field(self):
        headers = self.login_and_get_token()
        payload = {
            "password": "newpassword123", 
            "role": "admin"  
        }
        response = self.client.patch(f'/customers/{self.customer_id}', json=payload, headers=headers)
        
        # The route actually returns 403 status code for forbidden fields
        self.assertEqual(response.status_code, 403)
        
        # Check the error message matches what's returned by the route
        self.assertIn("cannot be updated by customer", response.get_json()["message"])
