from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select

from core.database import get_session
from models.user import User, Account, AccountType
from utils.password_helper import hash_password, verify_password


def create_user(nickname: str, email: str, password: str) -> Tuple[User, Account]:
    with get_session() as session:
        existing_account = session.scalars(
            select(Account).where(
                Account.account_type == AccountType.EMAIL,
                Account.identifier == email
            )
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
    with get_session() as session:
        account = session.scalars(
            select(Account).where(
                Account.account_type == AccountType.EMAIL,
                Account.identifier == email
            )
        ).first()

        if not account or not verify_password(password, account.credential):
            return None

        user = session.get(User, account.user_id)
        if not user:
            return None

        account.last_login_at = datetime.now()
        session.commit()

    return user, account


def get_user_by_id(user_id: int) -> Optional[User]:
    with get_session() as session:
        return session.get(User, user_id)


def get_user_by_email(email: str) -> Optional[Tuple[User, Account]]:
    with get_session() as session:
        account = session.scalars(
            select(Account).where(
                Account.account_type == AccountType.EMAIL,
                Account.identifier == email
            )
        ).first()

        if not account:
            return None
        user = session.get(User, account.user_id)

    return user, account if user else None


def update_user(user_id: int, nickname: str = None, avatar: str = None) -> Optional[User]:
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
    with get_session() as session:
        account = session.get(Account, account_id)
        if not account:
            return False

        account.is_verified = True
        session.commit()

        return True
