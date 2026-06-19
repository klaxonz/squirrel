from collections.abc import Callable, Generator
from datetime import datetime

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.user.domain.models.user import Account, AccountType, User
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]


class UserService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    @staticmethod
    def hash_password(password: str) -> str:
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    def create_user(self, nickname: str, email: str, password: str) -> tuple[User, Account]:
        with self._session_factory() as session:
            existing_account = session.scalars(
                select(Account).where(
                    Account.account_type == AccountType.EMAIL,
                    Account.identifier == email,
                ),
            ).first()

            if existing_account:
                raise ValueError('邮箱已被注册')

            user = User(nickname=nickname)
            session.add(user)
            session.flush()

            account = Account(
                user_id=user.id,
                account_type=AccountType.EMAIL,
                identifier=email,
                credential=self.hash_password(password),
                is_verified=False,
                last_login_at=datetime.now(),
            )
            session.add(account)
            session.commit()

        return user, account

    @staticmethod
    def _get_email_account_by_user_id(session: Session, user_id: int) -> Account | None:
        return session.scalars(
            select(Account).where(
                Account.user_id == user_id,
                Account.account_type == AccountType.EMAIL,
            ),
        ).first()

    def get_email_account_by_user_id(self, user_id: int) -> Account | None:
        with self._session_factory() as session:
            return self._get_email_account_by_user_id(session, user_id)

    def authenticate(self, email: str, password: str) -> tuple[User, Account] | None:
        with self._session_factory() as session:
            account = session.scalars(
                select(Account).where(
                    Account.account_type == AccountType.EMAIL,
                    Account.identifier == email,
                ),
            ).first()

            if not account or not self.verify_password(password, account.credential):
                return None

            user = session.get(User, account.user_id)
            if not user:
                return None

            account.last_login_at = datetime.now()
            session.commit()

        return user, account

    def get_user_by_id(self, user_id: int) -> User | None:
        with self._session_factory() as session:
            return session.get(User, user_id)

    def update_password(self, user_id: int, current_password: str, new_password: str) -> tuple[User, Account]:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if not user:
                raise ValueError('用户不存在')

            account = self._get_email_account_by_user_id(session, user_id)
            if not account:
                raise ValueError('邮箱账号不存在')

            if not self.verify_password(current_password, account.credential):
                raise ValueError('当前密码错误')

            if self.verify_password(new_password, account.credential):
                raise ValueError('新密码不能与当前密码相同')

            account.credential = self.hash_password(new_password)
            account.last_login_at = datetime.now()
            user.token_version = int(user.token_version or 0) + 1
            session.commit()
            session.refresh(user)
            session.refresh(account)

        return user, account

    def rotate_token_version(self, user_id: int) -> User:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if not user:
                raise ValueError('用户不存在')

            user.token_version = int(user.token_version or 0) + 1
            session.commit()
            session.refresh(user)

        return user

    def update_user(self, user_id: int, nickname: str | None = None, avatar: str | None = None) -> User | None:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if not user:
                return None

            if nickname:
                user.nickname = nickname
            if avatar:
                user.avatar = avatar

            session.commit()

        return user


user_service = UserService()
hash_password = user_service.hash_password
verify_password = user_service.verify_password
create_user = user_service.create_user
get_email_account_by_user_id = user_service.get_email_account_by_user_id
authenticate = user_service.authenticate
get_user_by_id = user_service.get_user_by_id
update_password = user_service.update_password
rotate_token_version = user_service.rotate_token_version
update_user = user_service.update_user
