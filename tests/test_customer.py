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

    # 1- Valid creation
    def test_create__customer(self):
        payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "1234567890",
            "password": 'test1234'
        }
        response = self.client.post('/customers/', json=payload)
        data = response.get_json()
        print(f'DATA: {data}')
        self.assertEqual(response.status_code, 201)
        # Check if got back valid data
        self.assertEqual(data["name"], "Jane Doe")
        
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
        self.assertIn("token", response.get_json())

    # 6- Get all customers
    def test_get__customers(self):
        response = self.client.get('/customers/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.json[0])
        
    # 7- Get single customer (authenticated route)
    def test_get__single_customer(self):
        # Get authorization token
        headers = self.login_and_get_token()
        response = self.client.get(f'/customers/{self.customer_id}', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], 'Test Customer')
        self.assertEqual(data['email'], 'test@test.com')

    # 8- Get my profile
    def test_get_my_profile(self):
        headers = self.login_and_get_token()
        response = self.client.get("/customers/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["email"], "test@test.com")
    
    # 9- Update a customer
    def test_update__customer(self):
        headers = self.login_and_get_token()
        payload = {
            "name": "Updated Customer",
            "phone": "1112223333",
            "email": "test@test.com", 
            "password": 'test1234'
        }
        response = self.client.put(f'/customers/{self.customer_id}', json=payload, headers=headers)
        self.assertEqual(response.status_code, 200)
        # not dublicate email since belogs to the id

    # 10- Partial update a customer
    def test_patch__customer(self):
        headers = self.login_and_get_token()
        payload = {
            "name": "The Customer"
        }
        response = self.client.patch(f'/customers/{self.customer_id}', json=payload, headers=headers)
        self.assertEqual(response.status_code, 200)
    
    # 11- Delete a customer
    def test_delete_customer(self):
        # Log in to get token
        headers = self.login_and_get_token()
        response = self.client.delete('/customers/', headers=headers)
        if response.status_code != 204:
            print("DELETE RESPONSE JSON:", response.get_json())
        
        self.assertIn(response.status_code, [204])
        
    # 12- Delete a customer with tickets
    def test_delete_customer_with_tickets(self):
        with self.app.app_context():
            # Create a ticket for our customer
            ticket = ServiceTicket(
                customer_id=self.customer_id,
                vin="ABC123456789DEF12",
                work_summary="Oil change needed",
                cost=50.00,
                status="open"
            )
            db.session.add(ticket)
            db.session.commit()
        
        # Log in and get a token
        headers = self.login_and_get_token()
        
        # Try to delete the customer
        response = self.client.delete('/customers/', headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Cannot delete customer", response.get_json()["message"])

                
        # Verify the customer still exists
        with self.app.app_context():
            customer = db.session.get(Customer, self.customer_id)
            self.assertIsNotNone(customer)
            
    # 13- Token decode direct
    def test_token_decode_direct(self):
        with self.app.app_context():
            login_payload = {"email": "test@test.com", "password": "test1234"}
            login_response = self.client.post("/customers/login", json=login_payload)
            token = login_response.get_json()["token"]

            try:
                decoded = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                print("TOKEN DECODED:", decoded)
            except Exception as e:
                print("MANUAL TOKEN DECODE ERROR:", e)

    # 13- Login
    def test_valid_login(self):
        payload = {"email": "test@test.com", "password": "test1234"}
        response = self.client.post("/customers/login", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.get_json())

    # 14- Invalid password
    def test_invalid_password(self):
        payload = {"email": "test@test.com", "password": "wrongpass"}
        response = self.client.post("/customers/login", json=payload)
        self.assertEqual(response.status_code, 401)    

    # 15- Nonexistent user
    def test_nonexistent_user(self):
        payload = {"email": "nouser@test.com", "password": "any"}
        response = self.client.post("/customers/login", json=payload)
        self.assertEqual(response.status_code, 401)

    # 16- test_phone_length_or_format
    def test_phone_length_or_format(self):
        payload = {"name": "Test Customer", "email": "test@test.com", "phone": "12345678901234567890", "password": "test1234"}
        response = self.client.post("/customers/", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone', response.get_json()['errors'])
        
    
    # 17- Get all tickets for a customer (authenticated route)
    def test_get_my_all_tickets(self):
        with self.app.app_context():
            ticket1 = ServiceTicket(
                customer_id=self.customer_id,
                vin="VIN001",
                work_summary="Check brakes",
                cost=100.00,
                status="open"
            )
            ticket2 = ServiceTicket(
                customer_id=self.customer_id,
                vin="VIN002",
                work_summary="Change oil",
                cost=40.00,
                status="closed"
            )
            db.session.add_all([ticket1, ticket2])
            db.session.commit()

        headers = self.login_and_get_token()
        
        response = self.client.get("/customers/me/tickets", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 2)
        
    # 18- Get tickets with status filter (authenticated route)
    def test_get_my_tickets_with_status_filter(self):
        with self.app.app_context():
            ticket = ServiceTicket(
                customer_id=self.customer_id,
                vin="VIN001",
                work_summary="Check brakes",
                cost=100.00,
                status="open"
            )
            db.session.add(ticket)
            db.session.commit()

        headers = self.login_and_get_token()

        response = self.client.get("/customers/me/tickets?status=open", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)
        self.assertEqual(response.get_json()[0]["status"], "open")


    # 19- Update password (authenticated route)
    def test_update_password(self):
        headers = self.login_and_get_token()

        update_payload = {
            "old_password": "test1234",
            "new_password": "newpass456"
        }
        response = self.client.patch("/customers/update-password", json=update_payload, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Password updated", response.get_json()["message"])
        
    # Helper method for authentication
    def login_and_get_token(self):
        login_payload = {"email": "test@test.com", "password": "test1234"}
        login_response = self.client.post("/customers/login", json=login_payload)
        token = login_response.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        return headers
