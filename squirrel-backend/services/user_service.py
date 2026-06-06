import bcrypt
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_session
from models.user import User, Account, AccountType


def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


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


def _get_email_account_by_user_id(session: Session, user_id: int) -> Optional[Account]:
    return session.scalars(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == AccountType.EMAIL
        )
    ).first()


def get_email_account_by_user_id(user_id: int) -> Optional[Account]:
    with get_session() as session:
        return _get_email_account_by_user_id(session, user_id)


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


def update_password(user_id: int, current_password: str, new_password: str) -> Tuple[User, Account]:
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        account = _get_email_account_by_user_id(session, user_id)
        if not account:
            raise ValueError('邮箱账号不存在')

        if not verify_password(current_password, account.credential):
            raise ValueError('当前密码错误')

        if verify_password(new_password, account.credential):
            raise ValueError('新密码不能与当前密码相同')

        account.credential = hash_password(new_password)
        account.last_login_at = datetime.now()
        user.token_version = int(user.token_version or 0) + 1
        session.commit()
        session.refresh(user)
        session.refresh(account)

    return user, account


def rotate_token_version(user_id: int) -> User:
    with get_session() as session:
        user = session.get(User, user_id)
        if not user:
            raise ValueError('用户不存在')

        user.token_version = int(user.token_version or 0) + 1
        session.commit()
        session.refresh(user)

    return user


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
