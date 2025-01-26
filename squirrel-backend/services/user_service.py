from datetime import datetime
from typing import Optional, Tuple
from core.database import get_session
from models.user import User, Account, AccountType
from utils.password_helper import hash_password, verify_password


def create_user(nickname: str, email: str, password: str) -> Tuple[User, Account]:
    """
    Create a new user with email account
    """
    with get_session() as session:
        # Check if email already exists
        existing_account = session.query(Account).filter(
            Account.account_type == AccountType.EMAIL,
            Account.identifier == email
        ).first()
        
        if existing_account:
            raise ValueError("邮箱已被注册")

        user = User(nickname=nickname)
        session.add(user)
        session.flush()

        account = Account(
            user_id=user.id,
            account_type=AccountType.EMAIL,
            identifier=email,
            credential=hash_password(password),
            is_verified=False,
            last_login_at=datetime.now()
        )
        session.add(account)
        session.commit()

    return user, account


def authenticate(email: str, password: str) -> Optional[Tuple[User, Account]]:
    """
    Authenticate user with email and password
    """
    with get_session() as session:
        account = session.query(Account).filter(
            Account.account_type == AccountType.EMAIL,
            Account.identifier == email
        ).first()

        if not account or not verify_password(password, account.credential):
            return None

        user = session.query(User).get(account.user_id)
        if not user:
            return None

        account.last_login_at = datetime.now()
        session.commit()

    return user, account


def get_user_by_id(user_id: int) -> Optional[User]:
    """
    Get user by ID
    """
    with get_session() as session:
        return session.get(User, user_id)


def get_user_by_email(email: str) -> Optional[Tuple[User, Account]]:
    """
    Get user by email
    """
    with get_session() as session:
        account = session.query(Account).filter(
            Account.account_type == AccountType.EMAIL,
            Account.identifier == email
        ).first()

        if not account:
            return None
        user = session.query(User).get(account.user_id)

    return user, account if user else None


def update_user(user_id: int, nickname: str = None, avatar: str = None) -> Optional[User]:
    """
    Update user profile
    """
    with get_session() as session:
        user = get_user_by_id(user_id)
        if not user:
            return None
        session.merge(user)
        if nickname:
            user.nickname = nickname
        if avatar:
            user.avatar = avatar

        session.commit()

    return user


def verify_account(account_id: int) -> bool:
    """
    Verify user account (e.g., after email verification)
    """
    with get_session() as session:
        account = session.query(Account).get(account_id)
        if not account:
            return False

        account.is_verified = True
        session.commit()

        return True
