import unittest
from application import create_app, db
from application.models import Inventory, SerializedPart

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
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop() # pop it safely

# 1- Create valid inventory
    def test_create_valid_inventory(self):
        payload = {
            "name": "Oil Filter",
            "inventory_number": "OIL-001",
            "desc": "Test Description",
            "price": "15.99",
            "quantity_in_stock": 50
        }

        response = self.client.post('/inventory/', json=payload)
        self.assertEqual(response.status_code, 201)

        data = response.get_json()
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
        response = self.client.post('/inventory/', json=payload)
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn("errors", data)
        self.assertIn("desc", data["errors"])
        
    # 3- duplicate inventory number
    def test_create_duplicate_inventory_number(self):
        payload = {
            "name": "Oil Filter",
            "inventory_number": "1234567890",
            "desc": "Test Description",
            "price": "15.99",
            "quantity_in_stock": 50
        }
        response = self.client.post('/inventory/', json=payload)
        self.assertEqual(response.status_code, 400)

        data = response.get_json()  
        self.assertIn("errors", data)
        self.assertIn("inventory_number", data["errors"])
        
    # 4- negative quantity
    def test_create_inventory_negative_quantity(self):
        payload = {
            "name": "Oil Filter",
            "inventory_number": "1234567891",
            "desc": "Test Description",
            "price": "15.99",
            "quantity_in_stock": -10
        }
        response = self.client.post('/inventory/', json=payload)
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn("errors", data)
        self.assertIn("quantity_in_stock", data["errors"])
        
    # 5- get all inventory
    def test_get_all_inventory(self):
        response = self.client.get('/inventory/')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
    
    # 6- get inventory by id
    def test_get_inventory_by_id(self):
        response = self.client.get(f'/inventory/{self.inventory.id}')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["id"], self.inventory.id)
        self.assertEqual(data["name"], self.inventory.name)
        
    # 7- get non-existent inventory by id
    def test_get_non_existent_inventory_by_id(self):
        response = self.client.get('/inventory/400')
        self.assertEqual(response.status_code, 404)

        data = response.get_json()
        self.assertEqual(data["error"], "Inventory not found")
        
    # 8- soft delete inventory
    def test_soft_delete_inventory(self):
        response = self.client.delete(f"/inventory/{self.inventory_id}")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["message"], "Inventory deleted (soft)")

        # Fetching the same inventory again 
        follow_up = self.client.get(f"/inventory/{self.inventory_id}")
        self.assertEqual(follow_up.status_code, 404)
        
        #? how cna i check db too


    #MARK: Serialzed parts
    # 1- create serialized part
    def test_create_serialized_part(self):
        payload = {
            "serial_number": "SP-002",
            "status": "available",
            "inventory_id": self.inventory.id
        }
        response = self.client.post('/inventory/serialized-parts/', json=payload) 
        self.assertEqual(response.status_code, 201)

        data = response.get_json()
        self.assertEqual(data["serial_number"], "SP-002")
        self.assertEqual(data["status"], "available")
        self.assertEqual(data["inventory_id"], self.inventory.id)

    #    2- create duplicate serialized part
    def test_create_duplicate_serialized_part(self):
        payload = {
            "serial_number": "SP-001",
            "status": "available",
            "inventory_id": self.inventory.id
        }
        response = self.client.post('/inventory/serialized-parts/', json=payload) 
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn("errors", data)
        self.assertIn("serial_number", data["errors"])
        
    # 3- create serialized part with invalid inventory id
    def test_create_serialized_part_with_invalid_inventory_id(self):
        payload = {
            "serial_number": "SP-003",
            "status": "available",
            "inventory_id": 99        
        }
        response = self.client.post('/inventory/serialized-parts/', json=payload) 
        self.assertEqual(response.status_code, 400)

        data = response.get_json()
        self.assertIn("errors", data)
        self.assertIn("inventory_id", data["errors"])
        
    # 4- get all serialized parts
    def test_get_all_serialized_parts(self):
        response = self.client.get('/inventory/serialized-parts/')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        
    # 5- get serialized part by id
    def test_get_serialized_part_by_id(self):
        response = self.client.get(f'/inventory/serialized-parts/{self.serialized_part_id}')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["id"], self.serialized_part_id)
        self.assertEqual(data["serial_number"], self.serialized_part.serial_number)

    # I dont delete - i coudl change their status maybe
    # 6 - patch the status part
    def test_patch_serialized_part_status(self):
        payload = {"status": "used"}
        
        response = self.client.patch(f'/inventory/serialized-parts/{self.serialized_part_id}', json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data["status"], "used")
        self.assertEqual(data["id"], self.serialized_part_id)        