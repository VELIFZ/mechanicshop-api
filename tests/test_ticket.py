import unittest
from application import create_app, db
from application.models import ServiceTicket, Employee, Service, Customer, Inventory, SerializedPart
from datetime import datetime



class TestServiceTicket(unittest.TestCase):
    def setUp(self):    
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()  
        self.app_context.push() 

        db.create_all()
        
            # Create a customer
        self.customer = Customer(
            name="Test Customer",
            email="test@example.com",
            phone="1234567890"
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

        response = self.client.post("/service-tickets/", json=payload)

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

        response = self.client.post("/service-tickets/", json=payload)
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

        response = self.client.post("/service-tickets/", json=payload)
        data = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(data["closed_at"])
    
    # 4- test linked models
    def test_create_with_related_objects(self):
        # Create related data
        employee = Employee(name="E1", email="e1@test.com", phone="123", password="pw", salary=5000, role="mechanic")
        service = Service(service_type="Brake Fix", base_price=100, description="Fixing brakes")
        inventory = Inventory(name="Brake Pad", inventory_number="BP001", price=50, desc="Brake pad", quantity_in_stock=10)
        part = SerializedPart(serial_number="SP001", status="used", inventory=inventory)

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

        response = self.client.post("/service-tickets/", json=payload)
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

        response = self.client.post("/service-tickets/", json=payload)
        data = response.get_json()

        print("STATUS:", response.status_code)
        print("BODY:", data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["cost"], 0.0)
        self.assertEqual(data["services"], [])
        self.assertEqual(data["serialized_parts"], [])

    
    # 6- fetch all tickets
    def test_get_all_service_tickets(self):
        response = self.client.get("/service-tickets/")
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("vin", data[0])
    
    # 7- get by id
    def test_get_ticket_by_id(self):
        response = self.client.get(f"/service-tickets/{self.ticket_id}")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["id"], self.ticket_id)
        self.assertEqual(data["vin"], self.ticket.vin)
        self.assertIn("customer", data)

    # 8 -  getting ticket with invalid id
    def test_get_ticket_by_invalid_id(self):
        response = self.client.get("/service-tickets/758")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", str(response.get_json()).lower())

    
    # 9- testing the output structure
    def test_get_all_tickets_structure(self):
        response = self.client.get("/service-tickets/")
        data = response.get_json()

        self.assertIsInstance(data, list)
        first = data[0]
        
        for field in ["id", "vin", "status", "customer", "services", "employees"]:
            self.assertIn(field, first)

    # 10 - see if no ricket
    def test_get_all_tickets_empty(self):
        db.session.query(ServiceTicket).delete()
        db.session.commit()

        response = self.client.get("/service-tickets/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("No service tickets", str(response.get_json()))

    # 11- patch
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

        response = self.client.patch(f"/service-tickets/{self.ticket_id}", json=payload)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "closed")
        self.assertEqual(data["work_summary"], payload["work_summary"])
        self.assertIsNotNone(data["closed_at"])
        self.assertGreater(data["cost"], 0)
        self.assertEqual(len(data["employees"]), 1)
        self.assertEqual(len(data["services"]), 1)
        self.assertEqual(len(data["serialized_parts"]), 1)

    # 12- delete
    def test_soft_delete_service_ticket(self):
        response = self.client.delete(f"/service-tickets/{self.ticket_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("soft-deleted", str(response.get_json()).lower())

        # Try to get the same ticket → should return 404
        get_response = self.client.get(f"/service-tickets/{self.ticket_id}")
        self.assertEqual(get_response.status_code, 404)
