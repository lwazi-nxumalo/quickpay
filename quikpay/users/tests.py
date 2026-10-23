from django.core.exceptions import ValidationError
from django.test import TestCase
from users.models import User

# Create your tests here

class UserModelTests(TestCase):
    def valid_user_data(self):
        return {
            "email": "user@example.com",
            "phone_number": "+27821111111",
            "id_number": "8809306122082",
            "first_name": "Test",
            "last_name": "User",
            "password": "password123",
        }

    def test_create_user_hashes_password(self):
        user = User.objects.create_user(**self.valid_user_data())

        self.assertEqual(user.email, "user@example.com")
        self.assertTrue(user.check_password("password123"))
        self.assertNotEqual(user.password, "password123")

    def test_email_is_required(self):
        data = self.valid_user_data()
        data["email"] = ""

        with self.assertRaises(ValueError):
            User.objects.create_user(**data)

    def test_phone_number_is_required(self):
        data = self.valid_user_data()
        data["phone_number"] = ""

        with self.assertRaises(ValueError):
            User.objects.create_user(**data)

    def test_id_number_is_validated(self):
        data = self.valid_user_data()
        data["id_number"] = "123"

        with self.assertRaises(ValidationError):
            User.objects.create_user(**data)

    def test_email_must_be_unique(self):
        User.objects.create_user(**self.valid_user_data())

        duplicate = self.valid_user_data()
        duplicate["phone_number"] = "+27822222222"
        duplicate["id_number"] = "8502025009082"

        with self.assertRaises(Exception):
            User.objects.create_user(**duplicate)
