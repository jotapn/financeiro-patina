import importlib
import os
import re
import sys
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.core.models import FamilyGroup, SecurityEvent, UserProfile
from apps.core.security import validate_upload_file


User = get_user_model()


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'security-hardening-tests',
        }
    },
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class SecurityHardeningTests(TestCase):
    def setUp(self):
        self._template_store_patch = mock.patch('django.test.client.store_rendered_templates', lambda *args, **kwargs: None)
        self._template_store_patch.start()
        cache.clear()
        mail.outbox = []

    def tearDown(self):
        self._template_store_patch.stop()

    def create_user(self, **kwargs):
        password = kwargs.pop('password', 'StrongPass123')
        user = User.objects.create_user(
            email=kwargs.pop('email', 'user@example.com'),
            username=kwargs.pop('username', 'user@example.com'),
            first_name=kwargs.pop('first_name', 'User'),
            last_name=kwargs.pop('last_name', 'Example'),
            password=password,
            **kwargs,
        )
        group = FamilyGroup.objects.create(name='Familia Teste')
        UserProfile.objects.create(user=user, family_group=group, role='admin')
        return user

    def test_valid_login_still_works(self):
        self.create_user()

        response = self.client.post('/auth/login/', {'email': 'user@example.com', 'password': 'StrongPass123'})

        self.assertRedirects(response, '/')
        self.assertTrue(SecurityEvent.objects.filter(event_type=SecurityEvent.LOGIN_SUCCESS).exists())

    @override_settings(RATE_LIMIT_LOGIN_LIMIT=2, RATE_LIMIT_LOGIN_WINDOW=300)
    def test_invalid_password_is_rate_limited_after_repeated_attempts(self):
        self.create_user()

        for _ in range(2):
            response = self.client.post('/auth/login/', {'email': 'user@example.com', 'password': 'wrong-pass'})
            self.assertEqual(response.status_code, 200)

        response = self.client.post('/auth/login/', {'email': 'user@example.com', 'password': 'wrong-pass'})

        self.assertEqual(response.status_code, 429)
        self.assertTrue(SecurityEvent.objects.filter(event_type=SecurityEvent.RATE_LIMITED).exists())

    def test_valid_register_still_works(self):
        response = self.client.post(
            '/auth/register/',
            {
                'email': 'new@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'password1': 'StrongPass123',
                'password2': 'StrongPass123',
            },
        )

        self.assertRedirects(response, '/')
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    @override_settings(MAX_UPLOAD_SIZE_MB=0, MAX_UPLOAD_SIZE_BYTES=0)
    def test_upload_above_limit_fails(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile('avatar.png', b'abc', content_type='image/png')

        with self.assertRaises(ValidationError):
            validate_upload_file(uploaded)

    def test_upload_with_invalid_extension_fails(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile('avatar.exe', b'abc', content_type='image/png')

        with self.assertRaises(ValidationError):
            validate_upload_file(uploaded)

    def test_security_events_are_audited_for_auth_and_invites(self):
        user = self.create_user()
        self.client.login(email='user@example.com', password='StrongPass123')

        self.client.get('/auth/logout/')
        self.assertTrue(SecurityEvent.objects.filter(event_type=SecurityEvent.LOGOUT, user=user).exists())

        self.client.login(email='user@example.com', password='StrongPass123')
        self.client.post('/family/invite/', {'email': 'guest@example.com'})
        self.assertTrue(SecurityEvent.objects.filter(event_type=SecurityEvent.INVITE_CREATED, user=user).exists())

    def test_staff_without_2fa_is_sent_to_setup_after_login(self):
        self.create_user(email='staff@example.com', username='staff@example.com', is_staff=True)

        response = self.client.post('/auth/login/', {'email': 'staff@example.com', 'password': 'StrongPass123'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('/profile/2fa/setup/'))

    def test_user_with_2fa_is_sent_to_challenge_after_login(self):
        user = self.create_user(email='totp@example.com', username='totp@example.com')
        TOTPDevice.objects.create(user=user, name='default', confirmed=True)

        response = self.client.post('/auth/login/', {'email': 'totp@example.com', 'password': 'StrongPass123'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('/profile/2fa/verify/'))

    def test_production_security_settings_are_enabled(self):
        env = {
            'SECRET_KEY': 'test-secret-key',
            'ALLOWED_HOSTS': 'app.example.com',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db?sslmode=require',
        }
        with mock.patch.dict(os.environ, env, clear=False):
            sys.modules.pop('config.settings.production', None)
            production = importlib.import_module('config.settings.production')

        self.assertTrue(production.SECURE_SSL_REDIRECT)
        self.assertTrue(production.SESSION_COOKIE_SECURE)
        self.assertTrue(production.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(production.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertTrue(production.CSRF_COOKIE_SECURE)
        self.assertFalse(production.CSRF_COOKIE_HTTPONLY)
        self.assertEqual(production.CSRF_COOKIE_SAMESITE, 'Lax')
        self.assertEqual(production.X_FRAME_OPTIONS, 'DENY')

    def test_production_rejects_wildcard_allowed_hosts(self):
        env = {
            'SECRET_KEY': 'test-secret-key',
            'ALLOWED_HOSTS': '*',
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db?sslmode=require',
        }
        with mock.patch.dict(os.environ, env, clear=False):
            sys.modules.pop('config.settings.production', None)
            with self.assertRaises(Exception):
                importlib.import_module('config.settings.production')

    def test_password_reset_page_opens(self):
        response = self.client.get('/auth/password-reset/')

        self.assertEqual(response.status_code, 200)

    def test_password_reset_existing_email_redirects_and_sends_email(self):
        self.create_user()

        response = self.client.post('/auth/password-reset/', {'email': 'user@example.com'})

        self.assertRedirects(response, '/auth/password-reset/done/')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/auth/reset/', mail.outbox[0].body)
        self.assertTrue(
            SecurityEvent.objects.filter(event_type=SecurityEvent.PASSWORD_RESET_REQUESTED).exists()
        )

    def test_password_reset_unknown_email_redirects_without_revealing_account(self):
        response = self.client.post('/auth/password-reset/', {'email': 'missing@example.com'})

        self.assertRedirects(response, '/auth/password-reset/done/')
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(
            SecurityEvent.objects.filter(event_type=SecurityEvent.PASSWORD_RESET_REQUESTED).exists()
        )

    def test_valid_password_reset_token_changes_password(self):
        user = self.create_user()
        self.client.post('/auth/password-reset/', {'email': 'user@example.com'})
        reset_path = self._reset_path_from_email()

        response = self.client.get(reset_path)
        self.assertEqual(response.status_code, 302)
        confirm_path = response['Location']

        response = self.client.post(
            confirm_path,
            {
                'new_password1': 'NewStrongPass123',
                'new_password2': 'NewStrongPass123',
            },
        )

        self.assertRedirects(response, '/auth/reset/done/')
        user.refresh_from_db()
        self.assertFalse(self.client.login(email='user@example.com', password='StrongPass123'))
        self.assertTrue(self.client.login(email='user@example.com', password='NewStrongPass123'))
        self.assertTrue(
            SecurityEvent.objects.filter(event_type=SecurityEvent.PASSWORD_RESET_SUCCESS, user=user).exists()
        )

    def test_invalid_password_reset_token_does_not_change_password(self):
        self.create_user()

        response = self.client.get('/auth/reset/bad-uid/bad-token/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.login(email='user@example.com', password='StrongPass123'))

    @override_settings(RATE_LIMIT_PASSWORD_RESET_LIMIT=1, RATE_LIMIT_PASSWORD_RESET_WINDOW=600)
    def test_password_reset_is_rate_limited_after_repeated_attempts(self):
        self.create_user()

        first = self.client.post('/auth/password-reset/', {'email': 'user@example.com'})
        second = self.client.post('/auth/password-reset/', {'email': 'user@example.com'})

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 429)
        self.assertTrue(SecurityEvent.objects.filter(event_type=SecurityEvent.RATE_LIMITED).exists())

    def test_password_reset_audit_does_not_store_password_or_token(self):
        self.create_user()

        self.client.post('/auth/password-reset/', {'email': 'user@example.com'})
        event = SecurityEvent.objects.filter(event_type=SecurityEvent.PASSWORD_RESET_REQUESTED).first()

        self.assertIsNotNone(event)
        metadata = event.metadata
        self.assertIn('email_hash', metadata)
        self.assertNotIn('email', metadata)
        self.assertNotIn('token', metadata)
        self.assertNotIn('password', metadata)

    def _reset_path_from_email(self):
        match = re.search(r'http://testserver(?P<path>/auth/reset/\S+)', mail.outbox[0].body)
        self.assertIsNotNone(match)
        return match.group('path')
