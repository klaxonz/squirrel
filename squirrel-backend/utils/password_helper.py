import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    """
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
