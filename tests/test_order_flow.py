import unittest
import os
os.environ.setdefault('SECRET_KEY', 'test-suite-ephemeral-secret-key-for-testing-only-12345')
os.environ.setdefault('OWNER_PASSWORD', 'TestOwner@Pass2026!')

import io
import tempfile
import json

from app import app
from database import init_db, get_db
from seed_data import seed_all

class TestOrderFlowAndUpiGating(unittest.TestCase):
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

    def test_complete_upi_order_lifecycle_and_gating(self):
        """Rule 3: Test full UPI flow with strict payment gating."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_units WHERE product_id = 1 AND multiplier = 1.0")
            unit_id = cursor.fetchone()['id']
            conn.close()

        # 1. Customer places order (3 x 45 = 135 > 100 min order)
        order_payload = {
            "items": [{"product_id": 1, "unit_id": unit_id, "quantity": 3}],
            "customer_name": "Vikas Yadav",
            "customer_phone": "9812345678",
            "delivery_type": "HOME_DELIVERY",
            "delivery_address": "Shop 4, Yadav Chowk",
            "payment_method": "ONLINE_UPI"
        }

        place_res = self.client.post('/api/orders', json=order_payload)
        self.assertEqual(place_res.status_code, 201)
        place_data = json.loads(place_res.data)
        order_id = place_data['order_id']
        guest_token = place_data['guest_token']
        self.assertEqual(place_data['status'], 'PENDING_OWNER_APPROVAL')

        # 2. Check Order Details before Owner Acceptance (UPI Gated)
        details_res_1 = self.client.get(f'/api/orders/{order_id}?token={guest_token}')
        self.assertEqual(details_res_1.status_code, 200)
        details_data_1 = json.loads(details_res_1.data)
        self.assertIsNone(details_data_1['upi_details'], "UPI details must remain hidden when PENDING_OWNER_APPROVAL")

        # 3. Owner logs in and accepts order
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'

        accept_res = self.client.post(f'/api/owner/orders/{order_id}/accept')
        self.assertEqual(accept_res.status_code, 200)
        self.assertEqual(json.loads(accept_res.data)['status'], 'ACCEPTED')

        # Clear session to act as customer again
        with self.client.session_transaction() as sess:
            sess.clear()

        # 4. Check Order Details after Owner Acceptance (UPI Unlocked)
        details_res_2 = self.client.get(f'/api/orders/{order_id}?token={guest_token}')
        details_data_2 = json.loads(details_res_2.data)
        self.assertIsNotNone(details_data_2['upi_details'], "UPI details must be revealed after order is ACCEPTED")
        self.assertIn('yadavstore@', details_data_2['upi_details']['upi_id'])
        self.assertIn('upi://pay', details_data_2['upi_details']['pay_uri'])

        VALID_PNG_BYTES = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        screenshot_file = (io.BytesIO(VALID_PNG_BYTES), "screenshot.png")
        upload_res = self.client.post(
            f'/api/orders/{order_id}/upload-payment',
            data={'screenshot': screenshot_file, 'token': guest_token},
            content_type='multipart/form-data'
        )
        self.assertEqual(upload_res.status_code, 200)
        self.assertEqual(json.loads(upload_res.data)['status'], 'PAYMENT_PENDING')

        # 6. Owner logs back in and verifies payment
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'

        verify_res = self.client.post(f'/api/owner/orders/{order_id}/verify-payment', json={
            "decision": "APPROVE",
            "notes": "Transaction confirmed in SBI UPI"
        })
        self.assertEqual(verify_res.status_code, 200)
        self.assertEqual(json.loads(verify_res.data)['status'], 'PAYMENT_VERIFIED')

        # 7. Move to processing and completed
        status_res = self.client.post(f'/api/owner/orders/{order_id}/status', json={"status": "COMPLETED"})
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(json.loads(status_res.data)['status'], 'COMPLETED')

    def test_cod_store_pickup_independent_from_upi(self):
        """Rule 4: COD/Pay at Store must work independently from UPI. Never show UPI details."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_units WHERE product_id = 1 AND multiplier = 1.0")
            unit_id = cursor.fetchone()['id']
            conn.close()

        order_payload = {
            "items": [{"product_id": 1, "unit_id": unit_id, "quantity": 3}],
            "customer_name": "Pooja",
            "customer_phone": "9765432100",
            "delivery_type": "STORE_PICKUP",
            "payment_method": "COD"
        }

        place_res = self.client.post('/api/orders', json=order_payload)
        self.assertEqual(place_res.status_code, 201)
        data = json.loads(place_res.data)
        order_id = data['order_id']
        guest_token = data['guest_token']

        # Owner accepts order
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'

        accept_res = self.client.post(f'/api/owner/orders/{order_id}/accept')
        self.assertEqual(accept_res.status_code, 200)

        # Clear owner session
        with self.client.session_transaction() as sess:
            sess.clear()

        # Check order details: UPI must NOT be shown for COD
        details_res = self.client.get(f'/api/orders/{order_id}?token={guest_token}')
        details = json.loads(details_res.data)
        self.assertIsNone(details['upi_details'], "COD/Pay at store orders must NEVER show UPI payment details.")

if __name__ == '__main__':
    unittest.main()
