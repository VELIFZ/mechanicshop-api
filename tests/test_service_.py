import unittest
from application import create_app
from application.models import db, Service
from application.utils.utils import encode_token

# A test class that inherits from unittest.TestCase. -> gives access to all the test features like assertEqual().
class TestService(unittest.TestCase):
    # called before each test, prepare the test environment
    # bu creates app in "testing" config, creates test client, and connects to db then sets up a test db and a test client
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        # set up fixture
        self.service = Service(service_type="Oil Change", base_price=10.00, description="Standard oil change")
        with self.app.app_context():
            db.create_all()
            db.session.add(self.service)
            db.session.commit()
            self.service_id = self.service.id
            
            # Create token and auth headers
            self.token = encode_token(1, 'employee') # dummy employee token
            self.headers = {"Authorization": f"Bearer {self.token}"}

    # Called after each test. Cleans up the database/ test environment
    def tearDown(self):
        with self.app.app_context():
            db.drop_all()
    
    # ------- Create Tests -------
    # 1- Valid creation- sends valid data to endpoint and checks if response is correct
    def test_create_valid_service(self):
        payload = {
            "service_type": "Oil Change",
            "base_price": 49.99,
            "description": "Standard oil change service"
        }
        response = self.client.post('/services/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        
        response_data = response.get_json()
        self.assertIsNotNone(response_data)
        # this line because confirms api returns correct service, schema dump works, no bug mutatuin or dropping fields
        self.assertEqual(response_data["service_type"], "Oil Change")
        
    # 2 - Missing required field   
    def test_create_invalid_service(self):
        payload = {
            "service_type": "Oil Change",
            "base_price": 49.99
        }

        response = self.client.post('/services/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        
        response_data = response.get_json()
        self.assertIsNotNone(response_data)
        self.assertIn('errors', response_data)
        self.assertIn('description', response_data['errors'])

    #3 - allows variant services
    def test_create_non_duplicate_service(self):
        payload = {
            "service_type": "oil change",  # lowercase but should be normalized
            "base_price": 59.99,
            "description": "Premium package"
        }
        response = self.client.post('/services/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        
    # 4 - Reject exact duplicates
    def test_create_duplicate_service(self):
        payload = {
            "service_type": "Oil Change",  # title-cased
            "base_price": 19.99,
            "description": "Standard oil change"
        }
        response = self.client.post('/services/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        
        response_data = response.get_json()
        self.assertIsNotNone(response_data)
        self.assertEqual("Service with this type and description already exists.", response_data['message'])

    # ------- Get Tests -------
    # 1- Fetch all
    def test_get_all_services(self):
        response = self.client.get('/services/')
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        self.assertIsInstance(response_data, list)
        if response_data:
            self.assertIn("service_type", response_data[0])
     
    # 2- search by type
    def test_search_services_by_type(self):
        # First, create another service to have multiple in DB
        payload = {
            "service_type": "Tire Rotation",
            "base_price": 20.00,
            "description": "Rotating the tires"
        }
        self.client.post('/services/', json=payload, headers=self.headers)

        # Now search for "Oil Change"
        response = self.client.get('/services/?service_type=Oil Change')
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertGreaterEqual(len(response_data), 1)
        self.assertIn("Oil Change", [service["service_type"] for service in response_data])

    # 3 - Fetch by id 
    def test_get_single_service(self):
        response = self.client.get(f'/services/{self.service_id}')
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        self.assertEqual(response_data['service_type'], 'Oil Change')
    
    # 4 - 404 handling
    def test_get_nonexistent_service(self):
        response = self.client.get(f'/services/399')
        self.assertEqual(response.status_code, 404)
        
        response_data = response.get_json()
        self.assertIsNotNone(response_data)
        self.assertEqual('Service not found', response_data['message'])
        
    # ------- Update Tests -------
    # 1 - Valid full update
    def test_update_service(self):
        payload = {
            "service_type": "Brake Check",
            "base_price": 39.99,
            "description": "Full brake inspection"
        }
        response = self.client.put(f'/services/{self.service_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data["service_type"], "Brake Check")
    
    # 2 - invalid update input
    def test_update__invalid_service(self):
        payload = {
            "service_type": "Brake Check",
            "base_price": 39.99
        }
        response = self.client.put(f'/services/{self.service_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        
        response_data = response.get_json()
        self.assertIn('errors', response_data)
        self.assertIn('description', response_data['errors'])
        
    # ------- Patch Tests -------
    def test_patch_service(self):
        payload = {
            "description": "Updated just the description"
        }
        response = self.client.patch(f'/services/{self.service_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        self.assertEqual(response_data["description"], "Updated just the description")
    
    # ------- Delete Tests -------
    # 1 - delete and confirm 
    def test_delete__service(self):
        response = self.client.delete(f'/services/{self.service_id}', headers=self.headers)
        self.assertEqual(response.status_code, 204)
        
        #confirm is gone
        get_response = self.client.get(f'/services/{self.service_id}')
        self.assertEqual(get_response.status_code, 404)
    
    # 2 - 404 on delete
    def test_delete__nonexistent_service(self):
        response = self.client.delete(f'/services/388', headers=self.headers)
        self.assertEqual(response.status_code, 404)
        
        response_data = response.get_json()
        self.assertIsNotNone(response_data)
        self.assertEqual('Service not found', response_data['message'])
        