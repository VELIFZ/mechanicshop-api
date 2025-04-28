import unittest
from application import create_app, db
from application.models import Inventory, SerializedPart
from application.utils.utils import encode_token

class TestInventory(unittest.TestCase):
    def setUp(self):    
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()  # store it
        self.app_context.push()  # push it

        db.create_all()
        self.inventory = Inventory(
            name="Test Inventory",
            inventory_number="1234567890",
            price= "100.00",
            desc="Test Description",
            quantity_in_stock=10
        )   
        db.session.add(self.inventory)
        db.session.commit()
        self.inventory_id = self.inventory.id
        
         # serialized part linked to the inventory
        self.serialized_part = SerializedPart(
            serial_number="SP-001",
            status="available",
            inventory_id=self.inventory.id
        )
        db.session.add(self.serialized_part)
        db.session.commit()

        self.serialized_part_id = self.serialized_part.id
        
        self.token = encode_token(1, 'employee')
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop() # pop it safely
        
# ------- Create Tests -------

    def test_create_valid_inventory(self):
        payload = {
            "name": "Oil Filter",
            "inventory_number": "OIL-001",
            "desc": "Test Description",
            "price": "15.99",
            "quantity_in_stock": 50
        }
        response = self.client.post('/inventory/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        
        self.assertTrue(response.is_json)
        data = response.get_json()["data"]
        self.assertEqual(data["name"], "Oil Filter")
        self.assertEqual(data["price"], "15.99")
        self.assertEqual(data["quantity_in_stock"], 50)
        
    # 2- Create invalid inventory
    def test_create_invalid_inventory(self):
        payload = {
            "name": "Oil Filter",
            "price": 15.99,
            "quantity_in_stock": 50
        }
        response = self.client.post('/inventory/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        
        self.assertTrue(response.is_json)
        self.assertIn("errors", response.get_json())
        
    # 3- duplicate inventory number
    def test_create_duplicate_inventory_number(self):
        payload = {
            "name": "Oil Filter",
            "inventory_number": "1234567890",
            "desc": "Test Description",
            "price": "15.99",
            "quantity_in_stock": 50
        }
        response = self.client.post('/inventory/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        
        self.assertTrue(response.is_json)
        self.assertIn("inventory_number", response.get_json()["details"])
        
    # 4- negative quantity
    def test_create_inventory_negative_quantity(self):
        payload = {
            "name": "Oil Filter",
            "inventory_number": "1234567891",
            "desc": "Test Description",
            "price": "15.99",
            "quantity_in_stock": -10
        }
        response = self.client.post('/inventory/', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        
        self.assertTrue(response.is_json)
        self.assertIn("quantity_in_stock", response.get_json()["errors"])
        
# ------- Get Tests -------
    # 1- get all inventory
    def test_get_all_inventory(self):
        response = self.client.get('/inventory/?page=1&limit=10')
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
    
    # 2- get inventory by id
    def test_get_inventory_by_id(self):
        response = self.client.get(f'/inventory/{self.inventory.id}')
        self.assertEqual(response.status_code, 200)

        self.assertTrue(response.is_json)
        data = response.get_json()["data"]
        self.assertEqual(data["id"], self.inventory.id)
        
    # 3- get non-existent inventory by id
    def test_get_non_existent_inventory_by_id(self):
        response = self.client.get('/inventory/400')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.is_json)

        data = response.get_json()
        self.assertEqual(response.get_json()["message"], "Inventory not found")
        
# ------- PATCH Tests -------
    # 1- patch inventory

    def test_patch_inventory(self):
        payload = {
            "price": "150.00",
            "quantity_in_stock": 20
        }
        response = self.client.patch(
            f'/inventory/{self.inventory_id}',
            json=payload,
            headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        data = response.get_json()["data"]
        self.assertEqual(data["price"], "150.00")
        self.assertEqual(data["quantity_in_stock"], 20)

        with self.app.app_context():
            updated_inventory = db.session.get(Inventory, self.inventory_id)
            self.assertEqual(str(updated_inventory.price), "150.00")
            self.assertEqual(updated_inventory.quantity_in_stock, 20)
        
        
# ------- Delete Tests -------
    # 1- soft delete inventory
    def test_soft_delete_inventory(self):
        response = self.client.delete(f"/inventory/{self.inventory_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

        data = response.get_json()
        self.assertEqual(data["message"], "Inventory deleted (soft)")

        # Fetching the same inventory again 
        follow_up = self.client.get(f"/inventory/{self.inventory_id}")
        self.assertEqual(follow_up.status_code, 404)
        
        # DB check
        with self.app.app_context():
            deleted_inventory = db.session.get(Inventory, self.inventory_id)
            self.assertTrue(deleted_inventory.is_deleted)


# MARK: ------- Serialzed parts Tests -------
    # 1- create serialized part
    def test_create_serialized_part(self):
        payload = {
            "serial_number": "SP-002",
            "status": "available",
            "inventory_id": self.inventory.id
        }
        response = self.client.post('/inventory/serialized-parts/', json=payload, headers=self.headers) 
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.is_json)

        self.assertEqual(response.get_json()["data"]["serial_number"], "SP-002")

    #    2- create duplicate serialized part
    def test_create_duplicate_serialized_part(self):
        payload = {
            "serial_number": "SP-001",
            "status": "available",
            "inventory_id": self.inventory.id
        }
        response = self.client.post('/inventory/serialized-parts/', json=payload, headers=self.headers) 
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.is_json)

        data = response.get_json()
        self.assertEqual(data["message"], "This serialized part already exists")
        self.assertIn("serial_number", data["details"])
        
    # 3- create serialized part with invalid inventory id
    def test_create_serialized_part_with_invalid_inventory_id(self):
        payload = {
            "serial_number": "SP-003",
            "status": "available",
            "inventory_id": 99        
        }
        response = self.client.post('/inventory/serialized-parts/', json=payload, headers=self.headers) 
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertEqual(data["message"], "Inventory not found")
        self.assertIn("inventory_id", data["details"])
        
    # ------- Get Tests -------
    # 1- get all serialized parts
    def test_get_all_serialized_parts(self):
        response = self.client.get('/inventory/serialized-parts/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertIsInstance(data, list)
    
    # 2- get serialized part by id
    def test_get_serialized_part_by_id(self):
        response = self.client.get(f'/inventory/serialized-parts/{self.serialized_part_id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        
        self.assertEqual(response.get_json()["data"]["id"], self.serialized_part_id)    

    # 3- get non-existent serialized part by id
    def test_get_non_existent_serialized_part_by_id(self):
        response = self.client.get('/inventory/serialized-parts/9999')
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.is_json)
        
    # ------- PATCH Tests -------
    # 1- patch the status part
    def test_patch_serialized_part_status(self):
        payload = {"status": "used"}
        response = self.client.patch(f'/inventory/serialized-parts/{self.serialized_part_id}', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        
        self.assertEqual(response.get_json()["data"]["status"], "used")
        
    # 2- patch non-existent serialized part returns 404
    def test_patch_non_existent_serialized_part(self):
        payload = {"status": "used"}
        response = self.client.patch('/inventory/serialized-parts/9999', json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.is_json)   
        
        data = response.get_json()
        self.assertEqual(data["message"], "Serialized part not found")

    # ------- Delete Tests -------
    # 1- Soft delete serialized part
    def test_soft_delete_serialized_part(self):
        response = self.client.delete(f"/inventory/serialized-parts/{self.serialized_part_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        
        follow_up = self.client.get(f"/inventory/serialized-parts/{self.serialized_part_id}")
        self.assertEqual(follow_up.status_code, 404) 
        
        with self.app.app_context():
            deleted_part = db.session.get(SerializedPart, self.serialized_part_id)
            self.assertTrue(deleted_part.is_deleted)
        