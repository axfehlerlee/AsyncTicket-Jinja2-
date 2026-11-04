import bcrypt

from asyncticket.users.domain.service import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def hash(self, raw_password: str) -> str:
        password_bytes = raw_password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(
            password_bytes,
            salt,
        )

        return hashed_password.decode("utf-8")

    def verify(
        self,
        raw_password: str,
        hashed_password: str,
    ) -> bool:
        password_bytes = raw_password.encode("utf-8")
        hashed_password_bytes = hashed_password.encode("utf-8")

        return bcrypt.checkpw(
            password_bytes,
            hashed_password_bytes,
        )