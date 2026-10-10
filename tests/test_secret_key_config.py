import os
os.environ.setdefault('SECRET_KEY', 'test-suite-ephemeral-secret-key-for-testing-only-12345')

import sys
import subprocess
import unittest
from unittest import mock
import importlib

import config

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class TestSecretKeyConfiguration(unittest.TestCase):
    def tearDown(self):
        # Guarantee that config module is restored with a valid test secret key
        with mock.patch.dict(os.environ, {'SECRET_KEY': 'test-suite-ephemeral-secret-key-for-testing-only-12345'}):
            importlib.reload(config)

    def test_missing_secret_key_in_development_raises_runtime_error(self):
        """Missing SECRET_KEY in development mode must fail safely with clear error message."""
        env = os.environ.copy()
        env.pop('SECRET_KEY', None)
        env['FLASK_ENV'] = 'development'

        result = subprocess.run(
            [sys.executable, "-c", "import config"],
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FATAL SECURITY ERROR: SECRET_KEY environment variable MUST be explicitly set and non-empty", result.stderr)

    def test_missing_secret_key_in_production_raises_runtime_error(self):
        """Missing SECRET_KEY in production mode must fail safely with clear error message."""
        env = os.environ.copy()
        env.pop('SECRET_KEY', None)
        env['FLASK_ENV'] = 'production'

        result = subprocess.run(
            [sys.executable, "-c", "import config"],
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FATAL SECURITY ERROR: SECRET_KEY environment variable MUST be explicitly set and non-empty", result.stderr)

    def test_empty_secret_key_raises_runtime_error(self):
        """Empty string SECRET_KEY must fail safely with clear error message."""
        env = os.environ.copy()
        env['SECRET_KEY'] = ''
        env['FLASK_ENV'] = 'development'

        result = subprocess.run(
            [sys.executable, "-c", "import config"],
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FATAL SECURITY ERROR: SECRET_KEY environment variable MUST be explicitly set and non-empty", result.stderr)

    def test_whitespace_secret_key_raises_runtime_error(self):
        """Whitespace-only SECRET_KEY must fail safely with clear error message."""
        env = os.environ.copy()
        env['SECRET_KEY'] = '   \t  \n '
        env['FLASK_ENV'] = 'development'

        result = subprocess.run(
            [sys.executable, "-c", "import config"],
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FATAL SECURITY ERROR: SECRET_KEY environment variable MUST be explicitly set and non-empty", result.stderr)

    def test_valid_secret_key_in_development_succeeds(self):
        """Valid non-empty SECRET_KEY in development mode loads successfully."""
        test_val = 'test-dev-secret-key-sample-1234'
        env = os.environ.copy()
        env['SECRET_KEY'] = test_val
        env['FLASK_ENV'] = 'development'

        result = subprocess.run(
            [sys.executable, "-c", f"import config; assert config.Config.SECRET_KEY == '{test_val}'; assert config.Config.DEBUG is True"],
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Subprocess failed with stderr: {result.stderr}")

    def test_valid_secret_key_in_production_succeeds(self):
        """Valid non-empty SECRET_KEY in production mode loads successfully with secure cookie settings."""
        test_val = 'test-prod-secret-key-sample-5678'
        env = os.environ.copy()
        env['SECRET_KEY'] = test_val
        env['FLASK_ENV'] = 'production'

        result = subprocess.run(
            [sys.executable, "-c", f"import config; assert config.Config.SECRET_KEY == '{test_val}'; assert config.Config.DEBUG is False; assert config.Config.SESSION_COOKIE_SECURE is True"],
            cwd=PROJECT_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, f"Subprocess failed with stderr: {result.stderr}")

    def test_in_process_reload_with_mock_patch(self):
        """In-process reload behavior with mock.patch.dict."""
        # Test missing key raises RuntimeError
        env_no_key = dict(os.environ)
        env_no_key.pop('SECRET_KEY', None)
        with mock.patch.dict(os.environ, env_no_key, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                importlib.reload(config)
            self.assertIn("FATAL SECURITY ERROR: SECRET_KEY", str(ctx.exception))

        # Test valid key reload
        sample_key = 'temporary-in-process-test-secret-key'
        with mock.patch.dict(os.environ, {'SECRET_KEY': sample_key, 'FLASK_ENV': 'development'}):
            importlib.reload(config)
            self.assertEqual(config.Config.SECRET_KEY, sample_key)

    def test_preserved_configuration_settings(self):
        """Verify that all existing database, upload, cookie, and rate limit settings are preserved."""
        with mock.patch.dict(os.environ, {'SECRET_KEY': 'test-preservation-key', 'FLASK_ENV': 'development'}):
            importlib.reload(config)
            self.assertTrue(os.path.isabs(config.Config.DB_PATH))
            self.assertTrue(config.Config.DB_PATH.endswith('yadav_store.db'))
            self.assertTrue(os.path.isabs(config.Config.UPLOAD_FOLDER))
            self.assertTrue(config.Config.PAYMENTS_UPLOAD_FOLDER.endswith(os.path.join('uploads', 'payments')))
            self.assertTrue(config.Config.PRODUCTS_UPLOAD_FOLDER.endswith(os.path.join('uploads', 'products')))
            self.assertEqual(config.Config.ALLOWED_EXTENSIONS, {'png', 'jpg', 'jpeg', 'webp', 'gif'})
            self.assertEqual(config.Config.MAX_CONTENT_LENGTH, 16 * 1024 * 1024)
            self.assertTrue(config.Config.SESSION_COOKIE_HTTPONLY)
            self.assertEqual(config.Config.SESSION_COOKIE_SAMESITE, 'Lax')
            self.assertEqual(config.Config.MAX_FAILED_LOGIN_ATTEMPTS, 5)
            self.assertEqual(config.Config.LOGIN_LOCKOUT_SECONDS, 300)

if __name__ == '__main__':
    unittest.main()
