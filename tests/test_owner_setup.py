import os
os.environ.setdefault('SECRET_KEY', 'test-suite-ephemeral-secret-key-for-testing-only-12345')

import io
import sys
import tempfile
import unittest
from unittest import mock

from database import init_db, get_db
from seed_data import seed_owner, seed_all
from auth import verify_password, hash_password

class TestSecureOwnerSetup(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        init_db(self.db_path)

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

    def test_seed_owner_without_password_creates_no_owner(self):
        """When no password argument or environment variable is set, no owner is created."""
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ['SECRET_KEY'] = 'test-suite-ephemeral-secret-key-for-testing-only-12345'
            created = seed_owner(self.db_path)
            self.assertFalse(created)

            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'owner'")
            count = cursor.fetchone()[0]
            conn.close()

            self.assertEqual(count, 0, "No owner account should be provisioned without explicit credentials.")

    def test_seed_owner_with_whitespace_password_creates_no_owner(self):
        """Whitespace-only or empty password must be rejected and not create an owner."""
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ['SECRET_KEY'] = 'test-suite-ephemeral-secret-key-for-testing-only-12345'
            created = seed_owner(self.db_path, password='   ')
            self.assertFalse(created)

            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'owner'")
            count = cursor.fetchone()[0]
            conn.close()

            self.assertEqual(count, 0)

    def test_seed_owner_with_explicit_argument_provisions_owner(self):
        """Providing explicit credentials securely hashes password and creates owner."""
        test_pwd = "ExplicitOwnerPassword@2026"
        created = seed_owner(
            self.db_path,
            username="explicit_owner",
            password=test_pwd,
            full_name="Explicit Owner",
            phone="9876543210",
            address="Test Store Address"
        )
        self.assertTrue(created)

        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT username, password_hash, role, full_name, phone, address FROM users WHERE username = 'explicit_owner'")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row['role'], 'owner')
        self.assertEqual(row['full_name'], 'Explicit Owner')
        self.assertNotEqual(row['password_hash'], test_pwd, "Password must not be stored in plaintext.")
        self.assertTrue(verify_password(test_pwd, row['password_hash']))

    def test_seed_owner_with_owner_password_env_var(self):
        """Owner is provisioned using OWNER_PASSWORD environment variable."""
        test_pwd = "EnvOwnerPassword@2026"
        with mock.patch.dict(os.environ, {'OWNER_PASSWORD': test_pwd}):
            created = seed_owner(self.db_path)
            self.assertTrue(created)

            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash, role FROM users WHERE role = 'owner'")
            row = cursor.fetchone()
            conn.close()

            self.assertIsNotNone(row)
            self.assertEqual(row['username'], 'owner')
            self.assertTrue(verify_password(test_pwd, row['password_hash']))

    def test_seed_owner_with_initial_owner_password_env_var(self):
        """Owner is provisioned using INITIAL_OWNER_PASSWORD environment variable."""
        test_pwd = "InitialEnvPassword@2026"
        with mock.patch.dict(os.environ, {'INITIAL_OWNER_PASSWORD': test_pwd}, clear=True):
            os.environ['SECRET_KEY'] = 'test-suite-ephemeral-secret-key-for-testing-only-12345'
            created = seed_owner(self.db_path)
            self.assertTrue(created)

            conn = get_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash, role FROM users WHERE role = 'owner'")
            row = cursor.fetchone()
            conn.close()

            self.assertIsNotNone(row)
            self.assertTrue(verify_password(test_pwd, row['password_hash']))

    def test_seed_owner_does_not_overwrite_existing_owner(self):
        """Existing owner password and credentials must be preserved and not overwritten."""
        initial_pwd = "OriginalOwnerPassword@2026"
        seed_owner(self.db_path, username="owner", password=initial_pwd)

        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE role = 'owner'")
        original_hash = cursor.fetchone()['password_hash']
        conn.close()

        # Subsequent seed attempt with a different password
        second_attempt = seed_owner(self.db_path, username="owner", password="NewAttemptPassword@9999")
        self.assertFalse(second_attempt, "seed_owner must return False when owner already exists.")

        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE role = 'owner'")
        preserved_hash = cursor.fetchone()['password_hash']
        conn.close()

        self.assertEqual(original_hash, preserved_hash, "Existing owner password hash must remain untouched.")
        self.assertTrue(verify_password(initial_pwd, preserved_hash))
        self.assertFalse(verify_password("NewAttemptPassword@9999", preserved_hash))

    def test_seed_owner_never_prints_passwords_to_console(self):
        """Seed operations must never output or leak passwords to stdout or stderr."""
        secret_password = "SuperSecretUnprintedPassword!XYZ789"
        stdout_capture = io.StringIO()

        with mock.patch('sys.stdout', stdout_capture):
            seed_owner(self.db_path, password=secret_password)

        captured = stdout_capture.getvalue()
        self.assertNotIn(secret_password, captured, "Secret password must NEVER be printed to console output.")
        self.assertIn("Store owner 'owner' provisioned successfully.", captured)

if __name__ == '__main__':
    unittest.main()
