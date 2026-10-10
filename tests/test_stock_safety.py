import unittest
import os
os.environ.setdefault('SECRET_KEY', 'test-suite-ephemeral-secret-key-for-testing-only-12345')
os.environ.setdefault('OWNER_PASSWORD', 'TestOwner@Pass2026!')

import tempfile
import json
import sqlite3

from app import app
from database import init_db, get_db
from seed_data import seed_all

class TestStockSafety(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        app.config['DB_PATH'] = self.db_path
        app.config['TESTING'] = True
        self.client = app.test_client()

        with app.app_context():
            init_db(self.db_path)
            seed_all(self.db_path)

        # Login as owner for owner endpoints
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'
            sess['username'] = 'owner'

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

    def test_stock_not_deducted_on_order_placement(self):
        """Rule 5: Do NOT permanently deduct stock when customer only places an order."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, stock FROM products WHERE id = 1")
            initial_stock = cursor.fetchone()['stock']
            cursor.execute("SELECT id FROM product_units WHERE product_id = 1 AND multiplier = 5.0")
            unit_id = cursor.fetchone()['id']
            conn.close()

        # Place order for 2 units of 5kg Atta (10kg total, 2 x 225 = 450 > 100 min order)
        order_payload = {
            "items": [{"product_id": 1, "unit_id": unit_id, "quantity": 2}],
            "customer_name": "Ramesh Kumar",
            "customer_phone": "9876543210",
            "delivery_type": "HOME_DELIVERY",
            "delivery_address": "House 10, Sector 4",
            "payment_method": "ONLINE_UPI"
        }

        res = self.client.post('/api/orders', json=order_payload)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'PENDING_OWNER_APPROVAL')

        # Check stock is completely unchanged
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT stock FROM products WHERE id = 1")
            current_stock = cursor.fetchone()['stock']
            conn.close()

        self.assertEqual(current_stock, initial_stock, "Stock should NOT change upon order placement.")

    def test_exact_stock_deduction_on_owner_acceptance(self):
        """Rule 5: Deduct stock only when Owner accepts, and deduct the exact ordered quantity."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT stock FROM products WHERE id = 3") # Desi Toor Dal
            initial_stock = cursor.fetchone()['stock']
            cursor.execute("SELECT id FROM product_units WHERE product_id = 3 AND multiplier = 0.25")
            unit_id = cursor.fetchone()['id']
            conn.close()

        # Order 3 units of 250g (multiplier 0.25, 3 x 40 = 120 > 100 min order) -> exactly 0.75 kg deduction
        order_payload = {
            "items": [{"product_id": 3, "unit_id": unit_id, "quantity": 3}],
            "customer_name": "Anita Verma",
            "customer_phone": "9811122233",
            "delivery_type": "STORE_PICKUP",
            "payment_method": "COD"
        }

        res = self.client.post('/api/orders', json=order_payload)
        self.assertEqual(res.status_code, 201)
        order_id = json.loads(res.data)['order_id']

        # Owner accepts order
        accept_res = self.client.post(f'/api/owner/orders/{order_id}/accept')
        self.assertEqual(accept_res.status_code, 200)

        # Check stock is deducted by exactly 0.75 kg
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT stock FROM products WHERE id = 3")
            new_stock = cursor.fetchone()['stock']
            conn.close()

        expected_stock = round(initial_stock - 0.75, 3)
        self.assertEqual(new_stock, expected_stock, f"Expected stock {expected_stock}, found {new_stock}")

    def test_idempotent_acceptance_prevents_duplicate_deduction(self):
        """Rule 5: Prevent duplicate stock deduction from refresh/repeated actions."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT stock FROM products WHERE id = 1")
            initial_stock = cursor.fetchone()['stock']
            cursor.execute("SELECT id FROM product_units WHERE product_id = 1 AND multiplier = 1.0")
            unit_id = cursor.fetchone()['id']
            conn.close()

        order_payload = {
            "items": [{"product_id": 1, "unit_id": unit_id, "quantity": 3}],
            "customer_name": "Suresh",
            "customer_phone": "9998887776",
            "delivery_type": "STORE_PICKUP",
            "payment_method": "COD"
        }

        res = self.client.post('/api/orders', json=order_payload)
        self.assertEqual(res.status_code, 201)
        order_id = json.loads(res.data)['order_id']

        # First acceptance: deducts 3.0kg
        self.client.post(f'/api/owner/orders/{order_id}/accept')

        # Repeated acceptance attempts
        repeat_res_1 = self.client.post(f'/api/owner/orders/{order_id}/accept')
        repeat_res_2 = self.client.post(f'/api/owner/orders/{order_id}/accept')

        self.assertEqual(repeat_res_1.status_code, 200)
        self.assertEqual(repeat_res_2.status_code, 200)

        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT stock FROM products WHERE id = 1")
            final_stock = cursor.fetchone()['stock']
            conn.close()

        self.assertEqual(final_stock, initial_stock - 3.0, "Duplicate acceptance must NOT deduct stock more than once.")

    def test_rejection_leaves_stock_untouched(self):
        """Rule 5: Reject/cancel before acceptance must not reduce stock."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT stock FROM products WHERE id = 1")
            initial_stock = cursor.fetchone()['stock']
            cursor.execute("SELECT id FROM product_units WHERE product_id = 1 AND multiplier = 1.0")
            unit_id = cursor.fetchone()['id']
            conn.close()

        order_payload = {
            "items": [{"product_id": 1, "unit_id": unit_id, "quantity": 3}],
            "customer_name": "Kapil",
            "customer_phone": "9123456789",
            "delivery_type": "STORE_PICKUP",
            "payment_method": "COD"
        }

        res = self.client.post('/api/orders', json=order_payload)
        self.assertEqual(res.status_code, 201)
        order_id = json.loads(res.data)['order_id']

        # Owner rejects order
        reject_res = self.client.post(f'/api/owner/orders/{order_id}/reject', json={"reason": "Customer unreachable"})
        self.assertEqual(reject_res.status_code, 200)

        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT stock FROM products WHERE id = 1")
            current_stock = cursor.fetchone()['stock']
            conn.close()

        self.assertEqual(current_stock, initial_stock, "Rejected order must leave stock untouched.")

if __name__ == '__main__':
    unittest.main()
