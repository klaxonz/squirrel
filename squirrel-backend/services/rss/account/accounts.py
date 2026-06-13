from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.rss import RssAccount
from services.rss.account.serialization import serialize_account

UNSET = object()


def get_account(session: Session, user_id: int, account_id: int) -> RssAccount | None:
    return session.scalars(
        select(RssAccount).where(
            RssAccount.id == account_id,
            RssAccount.user_id == user_id,
            RssAccount.is_deleted.is_(False),
        ),
    ).first()


def config_from_account(account: RssAccount) -> Any:
    from services.rss.client._base import RssAccountConfig
    from services.rss.credential import decrypt_credential

    return RssAccountConfig(
        provider=account.provider,
        base_url=account.base_url,
        username=account.username,
        credential=decrypt_credential(account.credential_encrypted),
    )


def list_accounts(session: Session, user_id: int) -> list[dict[str, Any]]:
    accounts = session.scalars(
        select(RssAccount)
        .where(RssAccount.user_id == user_id, RssAccount.is_deleted.is_(False))
        .order_by(RssAccount.created_at.desc()),
    ).all()
    return [serialize_account(account) for account in accounts]


def create_account(
    session: Session,
    user_id: int,
    *,
    provider: str,
    name: str,
    base_url: str,
    username: str | None,
    credential: str,
    enabled: bool,
    sync_entry_limit: int | None,
) -> dict[str, Any]:
    from services.rss.client._base import RssServiceError
    from services.rss.client._factory import normalize_base_url, normalize_provider, normalize_sync_entry_limit
    from services.rss.credential import encrypt_credential

    provider = normalize_provider(provider)
    base_url = normalize_base_url(base_url)
    sync_entry_limit = normalize_sync_entry_limit(provider, sync_entry_limit)
    name = str(name or '').strip()
    credential = str(credential or '').strip()
    if not name:
        raise RssServiceError('Account name is required')
    if not credential:
        raise RssServiceError('Credential is required')

    account = RssAccount(
        user_id=user_id,
        provider=provider,
        name=name,
        base_url=base_url,
        username=str(username or '').strip() or None,
        credential_encrypted=encrypt_credential(credential),
        enabled=bool(enabled),
        sync_entry_limit=sync_entry_limit,
        is_deleted=False,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return serialize_account(account)


def update_account(
    session: Session,
    account: RssAccount,
    *,
    provider: str | None,
    name: str | None,
    base_url: str | None,
    username: str | None,
    credential: str | None,
    enabled: bool | None,
    sync_entry_limit: Any,
) -> dict[str, Any]:
    from services.rss.client._base import RssServiceError
    from services.rss.client._factory import normalize_base_url, normalize_provider, normalize_sync_entry_limit
    from services.rss.credential import encrypt_credential

    if provider is not None:
        account.provider = normalize_provider(provider)
    if sync_entry_limit is not UNSET:
        account.sync_entry_limit = normalize_sync_entry_limit(account.provider, sync_entry_limit)
    elif provider is not None:
        account.sync_entry_limit = normalize_sync_entry_limit(account.provider, account.sync_entry_limit)
    if name is not None:
        normalized_name = str(name or '').strip()
        if not normalized_name:
            raise RssServiceError('Account name is required')
        account.name = normalized_name
    if base_url is not None:
        account.base_url = normalize_base_url(base_url)
    if username is not None:
        account.username = str(username or '').strip() or None
    if credential is not None and str(credential).strip():
        account.credential_encrypted = encrypt_credential(str(credential).strip())
    if enabled is not None:
        account.enabled = bool(enabled)
    session.commit()
    session.refresh(account)
    return serialize_account(account)


def delete_account(session: Session, account: RssAccount) -> bool:
    account.is_deleted = True
    account.enabled = False
    session.commit()
    return True


def test_account_config(
    *,
    provider: str,
    base_url: str,
    username: str | None,
    credential: str,
) -> dict[str, Any]:
    from services.rss.client._base import RssAccountConfig, RssServiceError
    from services.rss.client._factory import create_client, normalize_base_url, normalize_provider

    config = RssAccountConfig(
        provider=normalize_provider(provider),
        base_url=normalize_base_url(base_url),
        username=str(username or '').strip() or None,
        credential=str(credential or '').strip(),
    )
    if not config.credential:
        raise RssServiceError('Credential is required')
    feed_count = create_client(config).test_connection()
    return {'ok': True, 'feed_count': feed_count}


def test_account(account: RssAccount) -> dict[str, Any]:
    from services.rss.client._factory import create_client

    feed_count = create_client(config_from_account(account)).test_connection()
    return {'ok': True, 'feed_count': feed_count}
