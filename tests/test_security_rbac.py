import unittest
import os
os.environ.setdefault('SECRET_KEY', 'test-suite-ephemeral-secret-key-for-testing-only-12345')
TEST_OWNER_PASSWORD = os.environ.setdefault('OWNER_PASSWORD', 'TestOwner@Pass2026!')

import tempfile
import json
import uuid

from app import app
from database import init_db, get_db
from seed_data import seed_all
from auth import hash_password

class TestSecurityRBAC(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        app.config['DB_PATH'] = self.db_path
        app.config['TESTING'] = True
        self.client = app.test_client()

        with app.app_context():
            init_db(self.db_path)
            seed_all(self.db_path)

    def tearDown(self):
        try:
            os.close(self.db_fd)
        except OSError:
            pass
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass

    def test_unauthenticated_owner_access_is_blocked(self):
        """Unauthenticated user must be denied access to owner APIs."""
        res = self.client.get('/api/owner/orders')
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.data)
        self.assertIn("Owner access strictly required", data['error'])

    def test_customer_role_cannot_access_owner_apis(self):
        """Rule 2 & 6: Customer accounts must NEVER enter owner dashboard or APIs."""
        uname = f"cust_{uuid.uuid4().hex[:6]}"
        reg_payload = {
            "username": uname,
            "password": "CustomerPass123",
            "full_name": "Test Customer",
            "phone": "9876543210",
            "address": "Delhi"
        }
        reg_res = self.client.post('/api/auth/register', json=reg_payload)
        self.assertEqual(reg_res.status_code, 201)

        # Attempt to access owner endpoints as customer
        res1 = self.client.get('/api/owner/orders')
        self.assertEqual(res1.status_code, 403)

        res2 = self.client.post('/api/owner/orders/1/accept')
        self.assertEqual(res2.status_code, 403)

        res3 = self.client.get('/owner/dashboard', follow_redirects=False)
        self.assertIn(res3.status_code, (302, 403))

    def test_customer_data_isolation(self):
        """Rule 6: Never expose another customer's private data."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            
            # Insert Customer A
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone, address)
                VALUES ('cust_a_unique', ?, 'customer', 'Customer A', '9999999999', 'Private Address A')
            """, (hash_password('PassA123'),))
            user_a_id = cursor.lastrowid

            # Insert Customer B
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone, address)
                VALUES ('cust_b_unique', ?, 'customer', 'Customer B', '8888888888', 'Private Address B')
            """, (hash_password('PassB123'),))
            user_b_id = cursor.lastrowid

            # Customer A places an order
            cursor.execute("""
                INSERT INTO orders (
                    order_number, customer_id, customer_name, customer_phone,
                    delivery_type, delivery_address, subtotal, delivery_charge,
                    total_amount, payment_method, status
                ) VALUES (
                    'ORDER-A-SECRET-99', ?, 'Customer A', '9999999999',
                    'HOME_DELIVERY', 'Private Address A', 200, 30, 230, 'ONLINE_UPI', 'ACCEPTED'
                )
            """, (user_a_id,))
            order_a_id = cursor.lastrowid
            conn.commit()
            conn.close()

        # Login session as Customer B
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_b_id
            sess['role'] = 'customer'
            sess['username'] = 'cust_b_unique'

        # Customer B tries to view Customer A's order
        res = self.client.get(f'/api/orders/{order_a_id}')
        self.assertEqual(res.status_code, 403, "Customer B must NOT access Customer A's order details.")

    def test_owner_authenticated_access(self):
        """Owner with correct credentials successfully logs in and accesses dashboard APIs."""
        login_res = self.client.post('/api/owner/login', json={
            "username": "owner",
            "password": TEST_OWNER_PASSWORD
        })
        self.assertEqual(login_res.status_code, 200)

        orders_res = self.client.get('/api/owner/orders')
        self.assertEqual(orders_res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
