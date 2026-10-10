import os
os.environ.setdefault('SECRET_KEY', 'test-suite-ephemeral-secret-key-for-testing-only-12345')
TEST_OWNER_PASSWORD = os.environ.setdefault('OWNER_PASSWORD', 'TestOwner@Pass2026!')

import io
import tempfile
import json
import unittest

from app import app
from database import init_db, get_db
from seed_data import seed_all
from auth import hash_password, reset_failed_attempts

VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)

VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)

FAKE_IMAGE_BYTES = b"THIS IS NOT A VALID IMAGE! IT DOES NOT CONTAIN IMAGE MAGIC BYTES."

class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        app.config['DB_PATH'] = self.db_path
        app.config['TESTING'] = True
        self.client = app.test_client()

        with app.app_context():
            init_db(self.db_path)
            seed_all(self.db_path)

        # Reset rate limiter memory before every test run
        reset_failed_attempts('127.0.0.1', scope='login')
        reset_failed_attempts('127.0.0.1', scope='owner_login')

    def tearDown(self):
        reset_failed_attempts('127.0.0.1', scope='login')
        reset_failed_attempts('127.0.0.1', scope='owner_login')
        try:
            os.close(self.db_fd)
        except OSError:
            pass
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except PermissionError:
            pass

    def test_customer_login_rate_limiting(self):
        """Rule 10: After 5 failed customer login attempts, 6th attempt must return 429 Too Many Requests."""
        for i in range(5):
            res = self.client.post('/api/auth/login', json={
                'username': 'nonexistent_user',
                'password': 'wrongpassword'
            })
            self.assertEqual(res.status_code, 401, f"Attempt {i+1} should return 401")

        # 6th attempt must be rate limited
        blocked_res = self.client.post('/api/auth/login', json={
            'username': 'nonexistent_user',
            'password': 'wrongpassword'
        })
        self.assertEqual(blocked_res.status_code, 429)
        data = json.loads(blocked_res.data)
        self.assertIn("Too many failed login attempts", data['error'])

    def test_owner_login_rate_limiting(self):
        """Rule 10: After 5 failed owner login attempts, 6th attempt must return 429 Too Many Requests."""
        for i in range(5):
            res = self.client.post('/api/owner/login', json={
                'username': 'owner',
                'password': 'wrong_owner_password'
            })
            self.assertEqual(res.status_code, 401, f"Attempt {i+1} should return 401")

        # 6th attempt must be blocked
        blocked_res = self.client.post('/api/owner/login', json={
            'username': 'owner',
            'password': 'wrong_owner_password'
        })
        self.assertEqual(blocked_res.status_code, 429)
        data = json.loads(blocked_res.data)
        self.assertIn("Too many failed owner login attempts", data['error'])

    def test_owner_password_change_flow(self):
        """Rule 1: Secure owner password change API with validation and verification."""
        # 1. Unauthenticated change must fail
        unauth_res = self.client.post('/api/owner/change-password', json={
            'current_password': TEST_OWNER_PASSWORD,
            'new_password': 'NewOwnerPass@2026',
            'confirm_password': 'NewOwnerPass@2026'
        })
        self.assertEqual(unauth_res.status_code, 403)

        # 2. Log in as owner
        login_res = self.client.post('/api/owner/login', json={
            'username': 'owner',
            'password': TEST_OWNER_PASSWORD
        })
        self.assertEqual(login_res.status_code, 200)

        # 3. Wrong current password
        wrong_curr_res = self.client.post('/api/owner/change-password', json={
            'current_password': 'IncorrectCurrentPassword123',
            'new_password': 'NewStrongPassword@2026',
            'confirm_password': 'NewStrongPassword@2026'
        })
        self.assertEqual(wrong_curr_res.status_code, 401)
        self.assertIn("Current password is incorrect", json.loads(wrong_curr_res.data)['error'])

        # 4. Mismatched confirmation
        mismatch_res = self.client.post('/api/owner/change-password', json={
            'current_password': TEST_OWNER_PASSWORD,
            'new_password': 'NewStrongPassword@2026',
            'confirm_password': 'DifferentPassword@2026'
        })
        self.assertEqual(mismatch_res.status_code, 400)
        self.assertIn("do not match", json.loads(mismatch_res.data)['error'])

        # 5. Weak new password (too short or missing numbers)
        weak_res = self.client.post('/api/owner/change-password', json={
            'current_password': TEST_OWNER_PASSWORD,
            'new_password': 'short',
            'confirm_password': 'short'
        })
        self.assertEqual(weak_res.status_code, 400)

        # 6. Valid password change
        valid_res = self.client.post('/api/owner/change-password', json={
            'current_password': TEST_OWNER_PASSWORD,
            'new_password': 'NewOwnerPass@2026Updated',
            'confirm_password': 'NewOwnerPass@2026Updated'
        })
        self.assertEqual(valid_res.status_code, 200)

        # 7. Log out
        self.client.post('/api/auth/logout')

        # 8. Old password must no longer work
        old_login_res = self.client.post('/api/owner/login', json={
            'username': 'owner',
            'password': TEST_OWNER_PASSWORD
        })
        self.assertEqual(old_login_res.status_code, 401)

        # 9. New password must log in successfully
        new_login_res = self.client.post('/api/owner/login', json={
            'username': 'owner',
            'password': 'NewOwnerPass@2026Updated'
        })
        self.assertEqual(new_login_res.status_code, 200)

    def test_magic_byte_validation_rejects_disguised_files(self):
        """Rule 6: Fake image with disguised extension must be rejected."""
        # 1. Place order as guest
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_units WHERE product_id = 1 AND multiplier = 1.0")
            unit_id = cursor.fetchone()['id']
            conn.close()

        order_res = self.client.post('/api/orders', json={
            'customer_name': 'Proof Tester',
            'customer_phone': '9111111111',
            'delivery_type': 'HOME_DELIVERY',
            'delivery_address': 'Sector 4',
            'payment_method': 'ONLINE_UPI',
            'items': [{'product_id': 1, 'unit_id': unit_id, 'quantity': 4}]
        })
        self.assertEqual(order_res.status_code, 201)
        order_data = json.loads(order_res.data)
        order_id = order_data['order_id']
        guest_token = order_data['guest_token']

        # Accept order as owner to unlock upload
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'
        self.client.post(f'/api/owner/orders/{order_id}/accept')

        # Customer attempts uploading fake text file with .png extension
        fake_file = (io.BytesIO(FAKE_IMAGE_BYTES), "malicious.png")
        upload_res = self.client.post(
            f'/api/orders/{order_id}/upload-payment',
            data={'screenshot': fake_file, 'token': guest_token},
            content_type='multipart/form-data'
        )
        self.assertEqual(upload_res.status_code, 400)
        self.assertIn("Invalid image format", json.loads(upload_res.data)['error'])

        # Upload valid PNG succeeds
        valid_file = (io.BytesIO(VALID_PNG_BYTES), "proof.png")
        valid_upload_res = self.client.post(
            f'/api/orders/{order_id}/upload-payment',
            data={'screenshot': valid_file, 'token': guest_token},
            content_type='multipart/form-data'
        )
        self.assertEqual(valid_upload_res.status_code, 200)

    def test_payment_proof_strict_rbac_and_isolation(self):
        """Rule 5 & 11: Payment screenshot cannot be accessed publicly or by unauthorized customers."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone)
                VALUES ('cust_alpha', ?, 'customer', 'Customer Alpha', '9888888888')
            """, (hash_password('AlphaPass123'),))
            user_alpha_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone)
                VALUES ('cust_beta', ?, 'customer', 'Customer Beta', '9777777777')
            """, (hash_password('BetaPass123'),))
            user_beta_id = cursor.lastrowid

            cursor.execute("SELECT id FROM product_units WHERE product_id = 1 AND multiplier = 1.0")
            unit_id = cursor.fetchone()['id']
            conn.commit()
            conn.close()

        # Alpha logs in and places order
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_alpha_id
            sess['role'] = 'customer'

        order_res = self.client.post('/api/orders', json={
            'customer_name': 'Customer Alpha',
            'customer_phone': '9888888888',
            'delivery_type': 'HOME_DELIVERY',
            'delivery_address': 'Alpha Villa',
            'payment_method': 'ONLINE_UPI',
            'items': [{'product_id': 1, 'unit_id': unit_id, 'quantity': 4}]
        })
        self.assertEqual(order_res.status_code, 201)
        order_id = json.loads(order_res.data)['order_id']

        # Owner accepts order
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'
        self.client.post(f'/api/owner/orders/{order_id}/accept')

        # Alpha uploads payment screenshot
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_alpha_id
            sess['role'] = 'customer'
        png_file = (io.BytesIO(VALID_PNG_BYTES), "alpha_receipt.png")
        upload_res = self.client.post(
            f'/api/orders/{order_id}/upload-payment',
            data={'screenshot': png_file},
            content_type='multipart/form-data'
        )
        self.assertEqual(upload_res.status_code, 200)

        # 1. Direct access via /uploads/ must be strictly forbidden (403)
        direct_res = self.client.get(f'/uploads/payments/payment_{order_id}_proof.png')
        self.assertEqual(direct_res.status_code, 403)

        # 2. Owning Customer Alpha CAN access protected endpoint (200)
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_alpha_id
            sess['role'] = 'customer'
        alpha_access_res = self.client.get(f'/api/orders/{order_id}/payment-proof')
        self.assertEqual(alpha_access_res.status_code, 200)

        # 3. Owner CAN access protected endpoint (200)
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'
        owner_access_res = self.client.get(f'/api/orders/{order_id}/payment-proof')
        self.assertEqual(owner_access_res.status_code, 200)

        # 4. Another Customer Beta CANNOT access (403)
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_beta_id
            sess['role'] = 'customer'
        beta_access_res = self.client.get(f'/api/orders/{order_id}/payment-proof')
        self.assertEqual(beta_access_res.status_code, 403)

        # 5. Anonymous visitor CANNOT access (403)
        with self.client.session_transaction() as sess:
            sess.clear()
        anon_access_res = self.client.get(f'/api/orders/{order_id}/payment-proof')
        self.assertEqual(anon_access_res.status_code, 403)

    def test_notifications_lifecycle_and_mark_read(self):
        """Rule 2 & 11: Customer notifications list and mark-read API."""
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone)
                VALUES ('cust_notif', ?, 'customer', 'Notif User', '9666666666')
            """, (hash_password('NotifPass123'),))
            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO orders (
                    order_number, customer_id, customer_name, customer_phone,
                    delivery_type, subtotal, delivery_charge, total_amount, payment_method, status
                ) VALUES (
                    'ORDER-NOTIF-1', ?, 'Notif User', '9666666666',
                    'HOME_DELIVERY', 200, 30, 230, 'ONLINE_UPI', 'ACCEPTED'
                )
            """, (user_id,))
            order_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO notifications (user_id, order_id, message_en, message_hi, is_read)
                VALUES (?, ?, 'Order #123 accepted!', 'ऑर्डर स्वीकृत!', 0)
            """, (user_id, order_id))
            conn.commit()
            conn.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['role'] = 'customer'

        # 1. Fetch notifications
        get_res = self.client.get('/api/notifications')
        self.assertEqual(get_res.status_code, 200)
        notifs = json.loads(get_res.data)
        self.assertEqual(len(notifs), 1)
        self.assertEqual(notifs[0]['is_read'], 0)

        # 2. Mark as read
        mark_res = self.client.post('/api/notifications/mark-read')
        self.assertEqual(mark_res.status_code, 200)

        # 3. Verify marked read
        get_res_after = self.client.get('/api/notifications')
        notifs_after = json.loads(get_res_after.data)
        self.assertEqual(notifs_after[0]['is_read'], 1)

    def test_owner_asset_upload(self):
        """Rule 3 & 4: Owner can upload product photos and QR codes with magic byte validation."""
        # Unauthenticated upload is blocked
        fake_file = (io.BytesIO(VALID_PNG_BYTES), "asset.png")
        unauth_res = self.client.post(
            '/api/owner/upload',
            data={'file': fake_file},
            content_type='multipart/form-data'
        )
        self.assertEqual(unauth_res.status_code, 403)

        # Authenticated owner upload succeeds
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'

        png_file = (io.BytesIO(VALID_PNG_BYTES), "product_photo.png")
        auth_res = self.client.post(
            '/api/owner/upload',
            data={'file': png_file},
            content_type='multipart/form-data'
        )
        self.assertEqual(auth_res.status_code, 200)
        data = json.loads(auth_res.data)
        self.assertIn('/uploads/', data['url'])

    def test_owner_delete_product(self):
        """Rule 2 & 6: Owner can delete product, cascading units, and non-owner cannot."""
        # Unauthenticated delete blocked
        unauth_del = self.client.delete('/api/owner/products/1')
        self.assertEqual(unauth_del.status_code, 403)

        # Authenticated owner delete succeeds
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'owner'

        del_res = self.client.delete('/api/owner/products/1')
        self.assertEqual(del_res.status_code, 200)

        # Verify product removed from database
        with app.app_context():
            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM products WHERE id = 1")
            self.assertIsNone(cursor.fetchone())
            cursor.execute("SELECT id FROM product_units WHERE product_id = 1")
            self.assertEqual(len(cursor.fetchall()), 0)
            conn.close()

if __name__ == '__main__':
    unittest.main()
