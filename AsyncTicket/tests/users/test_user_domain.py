import unittest

from asyncticket.shared.core.exceptions import (
    ValidationException,
)
from asyncticket.users.domain.users import (
    User,
    UserRole,
)


class FakePasswordHasher:
    def hash(self, raw_password: str) -> str:
        return f"hashed:{raw_password}"

    def verify(
        self,
        raw_password: str,
        hashed_password: str,
    ) -> bool:
        return hashed_password == f"hashed:{raw_password}"


class UserDomainTests(unittest.TestCase):
    def test_create_user(self):
        user = User.create(
            email="test@example.com",
            name="테스트",
            raw_password="Password1!",
            phone_number="010-1234-5678",
            hasher=FakePasswordHasher(),
        )

        self.assertIsNone(user.user_id)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.name, "테스트")
        self.assertEqual(user.role, UserRole.BUYER)
        self.assertEqual(
            user.password_hash,
            "hashed:Password1!",
        )
        self.assertFalse(user.is_withdrawn)

    def test_email_is_normalized(self):
        user = User.create(
            email=" TEST@EXAMPLE.COM ",
            name="테스트",
            raw_password="Password1!",
            phone_number="010-1234-5678",
            hasher=FakePasswordHasher(),
        )

        self.assertEqual(
            user.email,
            "test@example.com",
        )

    def test_invalid_password_raises_exception(self):
        with self.assertRaises(ValidationException):
            User.create(
                email="test@example.com",
                name="테스트",
                raw_password="12345678",
                phone_number="010-1234-5678",
                hasher=FakePasswordHasher(),
            )

    def test_change_password(self):
        user = User.create(
            email="test@example.com",
            name="테스트",
            raw_password="Password1!",
            phone_number="010-1234-5678",
            hasher=FakePasswordHasher(),
        )

        user.change_password(
            old_password="Password1!",
            new_password="NewPassword1!",
            hasher=FakePasswordHasher(),
        )

        self.assertEqual(
            user.password_hash,
            "hashed:NewPassword1!",
        )

    def test_withdraw(self):
        user = User(
            user_id=1,
            email="test@example.com",
            name="테스트",
            password_hash="hashed:Password1!",
            role=UserRole.BUYER,
            phone_number="010-1234-5678",
        )

        user.withdraw(user)

        self.assertTrue(user.is_withdrawn)
        self.assertIsNotNone(user.deleted_at)


if __name__ == "__main__":
    unittest.main()