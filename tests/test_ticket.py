import unittest
from application import create_app, db
from application.models import ServiceTicket, Employee, Service, Customer, Inventory, SerializedPart
from application.utils.utils import encode_token

# --------- Helpers ---------
def create_inventory(name="Brake Pad", number="BP001", price=50.0):
    inventory = Inventory(
        name=name,
        inventory_number=number,
        price=price,
        desc="Auto part",
        quantity_in_stock=10
    )
    db.session.add(inventory)
    db.session.commit()
    return inventory

def create_serialized_part(serial_number="SP001", inventory_id=None):
    part = SerializedPart(
        serial_number=serial_number,
        status="available",
        inventory_id=inventory_id
    )
    db.session.add(part)
    db.session.commit()
    return part

def create_service(service_type="Brake Fix", base_price=100.0):
    service = Service(
        service_type=service_type,
        base_price=base_price,
        description="Standard service"
    )
    db.session.add(service)
    db.session.commit()
    return service

# --------- Test Class ---------
class TestServiceTicket(unittest.TestCase):
    def setUp(self):    
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()  
        self.app_context.push() 

        db.create_all()
        
        self.token = encode_token(1, 'employee') 
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
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
        
    def create_ticket(self, vin="VIN123", status="open", customer_id=None):
        ticket = ServiceTicket(
            vin=vin,
            work_summary="Some work",
            cost=0.0,
            status=status,
            customer_id=customer_id or self.customer_id
        )
        db.session.add(ticket)
        db.session.commit()
        return ticket
    
    # ------- Create Tests -------
    # 1- create valid ticket
    def test_create_valid_ticket(self):
        payload = {
            "vin": "1HGCM82633A004352",
            "work_summary": "Brake inspection completed",
            "status": "closed",
            "customer_id": self.customer.id
        }
        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        
        response_data = response.get_json()
        data = response_data["data"]
        self.assertEqual(data["vin"], payload["vin"])
        self.assertEqual(data["status"], payload["status"])

    # 2- create invalid ticket
    def test_create_invalid_ticket(self):
        payload = {
            "work_summary": "Oil change",
            "cost": 50.0,
            "status": "processing",  # not valid
            "customer_id": self.customer.id
        }
        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 422)
        
    # 3- create with extra field 
    def test_create_with_closed_status_sets_closed_at(self):
        payload = {
            "vin": "1HGCM82633A004352",
            "work_summary": "Complete repair",
            "status": "closed",
            "customer_id": self.customer.id
        }
        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.get_json()["data"]["closed_at"])
    
    # 4- test linked models
    def test_create_with_related_objects(self):
        # Create related data - testlerde bu kismi kontrol etmek icin
        employee = Employee(name="E1", email="e1@test.com", phone="123", password="pw", salary=5000, role="mechanic")
        service = create_service()
        inventory = create_inventory()
        part = create_serialized_part(inventory_id=inventory.id)
        
        db.session.add(employee)
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
        self.assertEqual(response.status_code, 201)
        
        response_data = response.get_json()
        data = response_data["data"]
        self.assertEqual(len(data["employees"]), 1)
        self.assertEqual(len(data["services"]), 1)
        self.assertEqual(len(data["serialized_parts"]), 1)

    # 5— edge case: no services/parts - yani inspection yapilacaksa service ve part olmayabilir
    def test_create_ticket_with_no_services_or_parts(self):
        payload = {
            "vin": "1HGCM82633A004352",
            "work_summary": "General inspection only",
            "status": "open",
            "customer_id": self.customer.id
        }
        response = self.client.post("/service-tickets/", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        
        response_data = response.get_json()
        data = response_data["data"]
        self.assertEqual(data["cost"], 0.0)

    # ------- Get Tests -------
    # 1- get all service tickets
    def test_get_all_service_tickets(self):
        response = self.client.get("/service-tickets/?page=1&limit=10", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        self.assertIn("data", response_data)

        # Check first ticket structure only if there are results
        if response_data["data"]:
            ticket = response_data["data"][0]
            self.assertIn("id", ticket)
            self.assertIn("vin", ticket)
            self.assertIn("status", ticket)

    # 2- get ticket by id
    def test_get_ticket_by_id(self):
        response = self.client.get(f"/service-tickets/{self.ticket_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)

    # 3- get ticket by invalid id
    def test_get_ticket_by_invalid_id(self):
        response = self.client.get("/service-tickets/758", headers=self.headers)
        self.assertEqual(response.status_code, 404)
        
        self.assertEqual(response.get_json()["status"], "error")

    # 4- get all tickets empty
    def test_get_all_tickets_empty(self):
        # Delete all tickets first
        with self.app.app_context():
            db.session.query(ServiceTicket).delete()
            db.session.commit()
            
        response = self.client.get("/service-tickets/", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.get_json()["data"], [])

    # 5- see if all tickets structure is correct
    def test_get_all_tickets_structure(self):
        response = self.client.get("/service-tickets/", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertIn("data", response_data)
        self.assertIn("meta", response_data)
        self.assertIn("pagination", response_data["meta"])

        data = response_data["data"]
        self.assertIsInstance(data, list)

        if data:
            ticket = data[0]
            for field in ["id", "vin", "status", "customer"]:
                self.assertIn(field, ticket)

    # 6- pagination
    def test_pagination_service_tickets(self):
        response = self.client.get("/service-tickets/?page=2&limit=5", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertIn("meta", response_data)
        self.assertIn("pagination", response_data["meta"])

    # 7- filter by customer id because
    def test_filter_service_tickets_by_customer_id(self):
        customer_id = self.customer.id

        response = self.client.get(f"/service-tickets/?customer_id={customer_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertIsInstance(data, list)

        if data:  # Only loop if there are tickets
            for ticket in data:
                self.assertEqual(ticket["customer"]["id"], customer_id)

    # 8- filter by status 
    def test_filter_service_tickets_by_status(self):
        response = self.client.get("/service-tickets/?status=open", headers=self.headers)
        self.assertEqual(response.status_code, 200)

        response_data = response.get_json()
        self.assertIn("data", response_data)
        data = response_data["data"]
        self.assertIsInstance(data, list)

        if data:  
            for ticket in data:
                self.assertIn("open", ticket["status"].lower())

    # ------- Update Tests -------
    # 1- patch ticket status and fields
    def test_patch_ticket_status_and_fields(self):
        ticket = self.create_ticket()
        payload = {
            "status": "closed",
            "work_summary": "Work completed"
        }
        response = self.client.patch(f"/service-tickets/{ticket.id}", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        response_data = response.get_json()
        data = response_data["data"]
        self.assertEqual(data["status"], "closed")
        self.assertIsNotNone(data["closed_at"])

    # 2- ticket cost calculation and status changes
    def test_ticket_status_transitions_and_cost(self):
        service = create_service()
        inventory = create_inventory()
        part = create_serialized_part(inventory_id=inventory.id)

        response = self.client.post("/service-tickets/", json={
            "vin": "STATUSTEST123",
            "work_summary": "Testing status transitions",
            "status": "open",
            "customer_id": self.customer_id
        }, headers=self.headers)
        ticket_id = response.get_json()["data"]["id"]

        update_payload = {"add_service_ids": [service.id], "add_part_ids": [part.id]}
        self.client.patch(f"/service-tickets/{ticket_id}", json=update_payload, headers=self.headers)

        close_payload = {"status": "closed"}
        response = self.client.patch(f"/service-tickets/{ticket_id}", json=close_payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(float(response.get_json()["data"]["cost"]), 0)
        
     # ------- Delete Tests -------
    # 1- soft delete
    def test_soft_delete_service_ticket(self):
        response = self.client.delete(f"/service-tickets/{self.ticket_id}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.get_json()["status"], "success")
        
        # Verify it's soft deleted (can't be retrieved)
        response_check = self.client.get(f"/service-tickets/{self.ticket_id}", headers=self.headers)
        self.assertEqual(response_check.status_code, 404)
        
