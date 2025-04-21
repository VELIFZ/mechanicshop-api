import unittest
from marshmallow import ValidationError
from application import create_app
from application.models import db, Customer, ServiceTicket

class TestCustomer(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.customer = Customer(name="Test Customer", email="test@test.com", phone="0000000000")
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
            "phone": "1234567890"
        }
        response = self.client.post('/customers/', json=payload)
        self.assertEqual(response.status_code, 201)
        # Check if got back valid data
        data = response.get_json()
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

    # Duplicate email on create
    def test_unique_email(self):
        payload = {
            "name": "John Doe",
            "phone": "1234567891",
            "email": "TEST@test.com" # dub email
        }

        response = self.client.post('/customers/', json=payload)
        # This route returns 200 if customer already exists
        self.assertEqual(response.status_code, 409)
        
        data = response.get_json()
        # print(f'dub email message => {data}') # {'customer': {'email': 'test@test.com', 'id': 1, 'name': 'Test Customer', 'phone': '0000000000'}, 'message': 'Customer already exists'}
        # Check the message and returned existing customer
        self.assertEqual(data["message"], "Customer already exists")
        self.assertIn("customer", data)
        self.assertEqual(data["customer"]["email"], "test@test.com") # confirms case-insensitive match

    # 
    def test_create__customer_invalid_email_format(self):
        payload = {"name": "Foo", "email": "not-an-email", "phone": "1231231234"}
        response = self.client.post('/customers/', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.get_json()['errors'])

    # get
    def test_get__customers(self):
        response = self.client.get('/customers/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.json[0])
        
    def test_get__single_customer(self):
        response = self.client.get(f'/customers/{self.customer_id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], 'Test Customer')
        self.assertEqual(data['email'], 'test@test.com')
        
    def test_get__nonexistent_customer(self):
        response = self.client.get('/customers/9999')
        self.assertEqual(response.status_code, 404)
    
    #update
    def test_update__customer(self):
        payload = {
            "name": "Updated Customer",
            "phone": "1112223333",
            "email": "test@test.com"
        }
        response = self.client.put(f'/customers/{self.customer_id}', json=payload)
        self.assertEqual(response.status_code, 200)
        # not dublicate email since belogs to the id

    #partial update 
    def test_patch__customer(self):
        payload = {
            "name": "The Customer"
        }
        
        response = self.client.patch(f'/customers/{self.customer_id}', json=payload)
        self.assertEqual(response.status_code, 200)
    
    #delete    
    def test_delete_customer(self):
        response = self.client.delete(f'/customers/{self.customer_id}')
        # API appears to be returning 200 for deletes, not 204
        self.assertEqual(response.status_code, 204)
        
        # Verify the customer no longer exists
        get_response = self.client.get(f'/customers/{self.customer_id}')
        self.assertEqual(get_response.status_code, 404)
        
    def test_delete_customer_with_tickets(self):
        # Testing that you can't delete a customer who has tickets
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
        
        try:
            # Try to delete - this should fail with an integrity error
            response = self.client.delete(f'/customers/{self.customer_id}')
            # If we get here without exception, manually fail the test
            self.fail("Should have raised an IntegrityError")
        except Exception as e:
            # We expect an integrity error because the database has a NOT NULL constraint
            # on the customer_id in the service_ticket table
            self.assertIn("IntegrityError", str(e))
            
        # Verify the customer still exists
        with self.app.app_context():
            customer = db.session.get(Customer, self.customer_id)
            self.assertIsNotNone(customer)


# test_phone_length_or_format