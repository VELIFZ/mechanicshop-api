import unittest
from application import create_app, db
from application.models import ServiceTicket, Employee, Service, Customer, Inventory, SerializedPart
from application.utils.utils import encode_token

class TestServiceTicket(unittest.TestCase):
    def setUp(self):    
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()  
        self.app_context.push() 

        db.create_all()
        
        self.token = encode_token(1, 'employee') 
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
            # Create a customer
        self.customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="1234567890",
            password="Password123"
        )
        db.session.add(self.customer)
        db.session.commit()
        self.customer_id = self.customer.id
        
        self.ticket = ServiceTicket(
            vin="1234567890",
            work_summary="Test Description",
            cost=10.0,
            status="closed",
            customer_id=self.customer.id
        )   
        db.session.add(self.ticket)
        db.session.commit()
        self.ticket_id = self.ticket.id
        
        
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop() 
        
    # 1- Create valid ticket
    def test_create_valid_ticket(self):
        payload = {
            "vin": "1HGCM82633A004352",
            "work_summary": "Brake inspection completed",
            "status": "closed",
            "customer_id": self.customer.id
        }

        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIsNotNone(data["id"])
        self.assertEqual(data["vin"], payload["vin"])
        self.assertEqual(data["status"], payload["status"])
    
    # 2- Create invalid ticket
    def test_create_invalid_ticket(self):
        payload = {
            #"vin": "1HGCM82633A004352",
            "work_summary": "Oil change",
            "cost": 50.0,
            "status": "processing",  # not valid
            "customer_id": self.customer.id
        }

        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 422)
        self.assertIn("status", str(response.get_json()))
        self.assertIn("vin", str(response.get_json()))
        
    # 3- create with extra field closed_at
    def test_create_with_closed_status_sets_closed_at(self):
        payload = {
            "vin": "1HGCM82633A004352",
            "work_summary": "Complete repair",
            "status": "closed",
            "customer_id": self.customer.id
        }

        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        data = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(data["closed_at"])
    
    # 4- test linked models
    def test_create_with_related_objects(self):
        # Create related data
        employee = Employee(name="E1", email="e1@test.com", phone="123", password="pw", salary=5000, role="mechanic")
        service = Service(service_type="Brake Fix", base_price=100, description="Fixing brakes")
        inventory = Inventory(name="Brake Pad", inventory_number="BP001", price=50, desc="Brake pad", quantity_in_stock=10)
        part = SerializedPart(serial_number="SP001", status="available", inventory=inventory)

        db.session.add_all([employee, service, inventory, part])
        db.session.commit()

        payload = {
            "vin": "TEST1234567890",
            "work_summary": "Full service",
            "status": "closed",
            "customer_id": self.customer.id,
            "employee_ids": [employee.id],
            "service_ids": [service.id],
            "part_ids": [part.id]
        }

        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        data = response.get_json()
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(data["employees"]), 1)
        self.assertEqual(len(data["services"]), 1)
        self.assertEqual(len(data["serialized_parts"]), 1)
        self.assertGreater(data["cost"], 0)

    # 5— edge case: no services/parts
    def test_create_ticket_with_no_services_or_parts(self):
        payload = {
            "vin": "1HGCM82633A004352",
            "work_summary": "General inspection only",
            "status": "open",
            "customer_id": self.customer.id
            # no employee_ids, service_ids, or part_ids
        }

        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        data = response.get_json()

        print("STATUS:", response.status_code)
        print("BODY:", data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["cost"], 0.0)
        self.assertEqual(data["services"], [])
        self.assertEqual(data["serialized_parts"], [])

    
    # 6- fetch all tickets
    def test_get_all_service_tickets(self):
        response = self.client.get("/service-tickets/?page=1&limit=10")
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIsInstance(data, list)  # my endpoint returns a list
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("vin", data[0])
    
    # 7- pagination
    def test_pagination_service_tickets(self):
        response = self.client.get("/service-tickets/?page=2&limit=5")
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIsInstance(data, list) # No need to check specific length, just type check
    
    # 8- filter by status
    def test_filter_service_tickets_by_status(self):
        response = self.client.get("/service-tickets/?status=open")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsInstance(data, list)
        for ticket in data:
            self.assertIn("open", ticket["status"].lower())
    
    # 9- filter by customer id
    def test_filter_service_tickets_by_customer_id(self):
        customer_id = self.customer.id  # or manually pass if you created a test customer

        response = self.client.get(f"/service-tickets/?customer_id={customer_id}")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIsInstance(data, list)
        for ticket in data:
            self.assertEqual(ticket["customer"]["id"], customer_id)


    # 10- get by id
    def test_get_ticket_by_id(self):
        response = self.client.get(f"/service-tickets/{self.ticket_id}")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["id"], self.ticket_id)
        self.assertEqual(data["vin"], self.ticket.vin)
        self.assertIn("customer", data)

    # 11 -  getting ticket with invalid id
    def test_get_ticket_by_invalid_id(self):
        response = self.client.get("/service-tickets/758")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", str(response.get_json()).lower())

    
    # 12- testing the output structure
    def test_get_all_tickets_structure(self):
        response = self.client.get("/service-tickets/")
        data = response.get_json()

        self.assertIsInstance(data, list)
        first = data[0]
        
        for field in ["id", "vin", "status", "customer", "services", "employees"]:
            self.assertIn(field, first)

    # 13 - see if no tickets returns empty list
    def test_get_all_tickets_empty(self):
        db.session.query(ServiceTicket).delete()
        db.session.commit()

        response = self.client.get("/service-tickets/")
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertEqual(data, [])

    # 14- patch
    def test_patch_ticket_status_and_fields(self):
        employee = Employee(name="Mech", email="mech@test.com", phone="123", password="pw", salary=5000, role="mechanic")
        service = Service(service_type="Tire Rotation", base_price=40.0, description="Rotate tires")
        inventory = Inventory(name="Tire", inventory_number="T123", price=80.0, desc="Rear tire", quantity_in_stock=5)
        part = SerializedPart(serial_number="PT100", status="used", inventory=inventory)

        db.session.add_all([employee, service, inventory, part])
        db.session.commit()

        payload = {
            "status": "closed",
            "work_summary": "Final tire service completed.",
            "employee_ids": [employee.id],
            "service_ids": [service.id],
            "part_ids": [part.id]
        }

        response = self.client.patch(f"/service-tickets/{self.ticket_id}", json=payload, headers=self.headers)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "closed")
        self.assertEqual(data["work_summary"], payload["work_summary"])
        self.assertIsNotNone(data["closed_at"])
        self.assertGreater(data["cost"], 0)
        self.assertEqual(len(data["employees"]), 1)
        self.assertEqual(len(data["services"]), 1)
        self.assertEqual(len(data["serialized_parts"]), 1)

    # 15- delete
    def test_soft_delete_service_ticket(self):
        response = self.client.delete(f"/service-tickets/{self.ticket_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        # Try to fetch the deleted ticket
        response = self.client.get(f"/service-tickets/{self.ticket_id}")
        self.assertEqual(response.status_code, 404)
    
    # 16- patch - edit add and remove mechanics 
    def test_edit_ticket_mechanics(self):
        # Create test mechanics
        mechanic1 = Employee(name="Mechanic 1", email="mechanic1@test.com", phone="1234567890", password="password", salary=60000, role="mechanic")
        mechanic2 = Employee(name="Mechanic 2", email="mechanic2@test.com", phone="0987654321", password="password", salary=55000, role="mechanic")
        db.session.add_all([mechanic1, mechanic2])
        db.session.commit()
        
        # First adding mechanic1
        payload = {
            "add_ids": [mechanic1.id],
            "remove_ids": []
        }
        response = self.client.put(f"/service-tickets/{self.ticket_id}/edit", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["employees"]), 1)
        self.assertEqual(data["employees"][0]["id"], mechanic1.id)
        
        # Now add mechanic2 and remove mechanic1
        payload = {
            "add_ids": [mechanic2.id],
            "remove_ids": [mechanic1.id]
        }
        response = self.client.put(f"/service-tickets/{self.ticket_id}/edit", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["employees"]), 1)
        self.assertEqual(data["employees"][0]["id"], mechanic2.id)
        
        # Test with invalid ticket ID
        response = self.client.put("/service-tickets/999/edit", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual("Ticket not found", response.get_json()["message"])

    # 17- add part to ticket
    def test_add_part_to_ticket(self):
        # Create test inventory and part
        inventory = Inventory(
            name="Test Part", 
            inventory_number="PART-123", 
            price=45.99, 
            desc="Test part description", 
            quantity_in_stock=10
        )
        db.session.add(inventory)
        db.session.commit()
        
        part = SerializedPart(
            serial_number="SN-12345",
            status="available",
            inventory_id=inventory.id
        )
        db.session.add(part)
        db.session.commit()
        
        # Add part to ticket
        response = self.client.post(f"/service-tickets/{self.ticket_id}/add-part/{part.id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Verify part was added
        self.assertEqual(len(data["serialized_parts"]), 1)
        self.assertEqual(data["serialized_parts"][0]["id"], part.id)
        
        # Verify part status was updated
        part_check = db.session.get(SerializedPart, part.id)
        self.assertEqual(part_check.status, "used")
        
        # Test with non-existent ticket
        response = self.client.post(f"/service-tickets/999/add-part/{part.id}", headers=self.headers)
        self.assertEqual(response.status_code, 404)
        
        # Create another part for testing invalid part ID
        another_part = SerializedPart(
            serial_number="SN-ANOTHER",
            status="available",
            inventory_id=inventory.id
        )
        db.session.add(another_part)
        db.session.commit()
        another_part.status = "used"  # Make it unavailable
        db.session.commit()
        
        # Test with unavailable part
        response = self.client.post(f"/service-tickets/{self.ticket_id}/add-part/{another_part.id}", headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("not available", response.get_json()["message"])
