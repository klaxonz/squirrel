import logging
import threading
import json
from typing import Dict, Any, List, Optional

from sqlalchemy import select

from core.database import get_session
from models.links import UserSubscription
from models.message import Message
from models.subscription import Subscription
from services import user_video_feed_service
from services import subscription_sync_state_service
from services.subscription_crud_service import (
    get_active_user_subscription_by_url,
    get_active_user_subscription_url_map,
    get_deleted_user_subscription_urls,
    get_subscription_by_id,
    get_subscription_by_url_and_name,
)
from services.subscription_manage_service import (
    create_subscription,
    restore_subscription,
    list_user_ids,
)
from services.subscription_runtime_models import (
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
)
from site_runtimes.manager import get_site_runtime_manager
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain, get_site_from_url
from common import constants
from queues.producer import RedisStreamProducer

logger = logging.getLogger(__name__)


def get_runtime_supported_sites(capability: str) -> List[str]:
    snapshot = get_site_runtime_manager().get_snapshot()
    return sorted({
        registration.site_name
        for registration in snapshot.registrations
        if registration.capability == capability and registration.site_name
    })


def get_enabled_runtime_import_sites() -> List[str]:
    return [
        site
        for site in get_runtime_supported_sites('import_subscriptions')
        if SiteCatalog.is_site_enabled(site=site)
    ]


def _load_runtime_subscription_meta(url: str) -> SubscriptionMeta:
    from urllib.parse import urlparse
    domain = extract_top_level_domain(url)
    parsed_url = urlparse(url)
    payload = {
        'url': url,
        'domain': domain or parsed_url.netloc.lower().split(':')[0],
    }
    response = get_site_runtime_manager().gateway.invoke(
        'resolve_subscription',
        payload=payload,
        domain=domain or None,
    )
    if not response.ok:
        message = response.error.message if response.error else f'Plugin subscription resolution failed for url: {url}'
        raise ValueError(message)

    if not isinstance(response.data, dict):
        raise ValueError(f'Plugin resolve_subscription payload must be an object for url: {url}')

    return SubscriptionMeta.from_dict(response.data)


def _dedupe_import_items(subscriptions: List[SubscriptionImportItem]) -> List[SubscriptionImportItem]:
    seen_urls = set()
    result = []
    for sub in subscriptions:
        if not sub.url or sub.url in seen_urls:
            continue
        seen_urls.add(sub.url)
        result.append(sub)
    return result


def _load_runtime_import_batch(
    site_name: str,
    *,
    cursor_payload: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> SubscriptionImportBatchResult:
    payload: Dict[str, Any] = {}
    if cursor_payload:
        payload['cursor_payload'] = dict(cursor_payload)
    if limit is not None:
        payload['limit'] = limit

    response = get_site_runtime_manager().gateway.invoke(
        'import_subscriptions',
        payload=payload or None,
        site_name=site_name,
    )
    if not response.ok:
        message = response.error.message if response.error else f'Plugin import failed for site: {site_name}'
        raise ValueError(message)

    payload = response.data
    if not isinstance(payload, dict):
        raise ValueError(f'Plugin import payload must be an object for site: {site_name}')

    batch = SubscriptionImportBatchResult.from_dict(payload)
    batch.items = _dedupe_import_items(batch.items)
    return batch


def _load_runtime_import_items(site_name: str) -> List[SubscriptionImportItem]:
    items: List[SubscriptionImportItem] = []
    cursor_payload: Optional[Dict[str, Any]] = None

    while True:
        batch = _load_runtime_import_batch(
            site_name,
            cursor_payload=cursor_payload,
        )
        items.extend(batch.items)
        if not batch.has_more:
            break
        cursor_payload = batch.cursor_payload

    return _dedupe_import_items(items)


def handle_subscribe_request(url: str, user_id: int) -> Subscription:
    existing_subscription = get_active_user_subscription_by_url(user_id=user_id, url=url)
    if existing_subscription:
        return existing_subscription

    subscribe_info = _load_runtime_subscription_meta(url)

    subscription = get_subscription_by_url_and_name(url, subscribe_info.name)

    if subscription:
        restore_subscription(subscription.id, user_id)
        return get_subscription_by_id(subscription.id)

    subscription = create_subscription(user_id, subscribe_info)
    return subscription


def preview_user_subscriptions(
    site_name: str,
    user_id: int,
    *,
    cursor_payload: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        import_batch = _load_runtime_import_batch(
            site_name,
            cursor_payload=cursor_payload,
            limit=limit,
        )
        subscriptions = import_batch.items

        logger.info(f"Found {len(subscriptions)} subscriptions from {site_name} for preview")

        imported_url_map = get_active_user_subscription_url_map(user_id)
        imported_count = 0

        preview_subscriptions = []
        for sub in subscriptions:
            data = sub.to_dict()
            is_imported = sub.url in imported_url_map
            data["is_imported"] = is_imported
            if is_imported:
                data["subscription_id"] = imported_url_map[sub.url]
                imported_count += 1
            preview_subscriptions.append(data)

        return {
            'site': site_name,
            'total': import_batch.total_available if import_batch.total_available is not None else len(subscriptions),
            'loaded': len(subscriptions),
            'imported': imported_count,
            'not_imported': len(subscriptions) - imported_count,
            'subscriptions': preview_subscriptions,
            'has_more': import_batch.has_more,
            'cursor_payload': import_batch.cursor_payload,
            'stop_reason': import_batch.stop_reason,
        }

    except Exception as e:
        logger.error(f"Failed to preview subscriptions from {site_name}: {e}", exc_info=True)
        raise


def _enqueue_subscriptions_async(subscriptions: List[SubscriptionImportItem], user_id: int, site_name: str):
    try:
        enqueued = 0
        producer = RedisStreamProducer()

        with get_session() as session:
            for sub in subscriptions:
                url = sub.url
                try:
                    task = {
                        "url": url,
                        "name": sub.name,
                        "avatar": sub.avatar,
                        "user_id": user_id
                    }
                    message = Message(body=json.dumps(task))
                    session.add(message)
                    session.flush()

                    dump_json = message.to_dict()
                    producer.send(constants.QUEUE_SUBSCRIBE, dump_json)
                    enqueued += 1

                except Exception as e:
                    logger.warning(f"Failed to enqueue subscription {url}: {e}")

            session.commit()

        logger.info(f"Enqueued {enqueued}/{len(subscriptions)} subscription tasks from {site_name}")

    except Exception as e:
        logger.error(f"Failed to enqueue subscriptions from {site_name}: {e}", exc_info=True)


def import_user_subscriptions(
    site_name: str,
    user_id: int,
    selected_urls: Optional[List[str]] = None,
    *,
    use_background_thread: bool = True,
    respect_manual_unsubscribe: bool = False,
) -> Dict[str, Any]:
    try:
        if selected_urls is not None:
            subscriptions = _dedupe_import_items([
                SubscriptionImportItem(url=url)
                for url in selected_urls
                if url
            ])
            found_total = None
        else:
            subscriptions = _load_runtime_import_items(site_name)
            found_total = len(subscriptions)
            logger.info(f"Found {found_total} subscriptions from {site_name}")
        selected_total = len(subscriptions)

        imported_url_map = get_active_user_subscription_url_map(user_id)
        imported_urls = set(imported_url_map.keys())
        manually_unsubscribed_urls = (
            get_deleted_user_subscription_urls(user_id)
            if respect_manual_unsubscribe
            else set()
        )
        to_import = [
            s for s in subscriptions
            if s.url not in imported_urls and s.url not in manually_unsubscribed_urls
        ]

        if to_import:
            if use_background_thread:
                thread = threading.Thread(
                    target=_enqueue_subscriptions_async,
                    args=(to_import, user_id, site_name),
                    daemon=True
                )
                thread.start()
                logger.info(f"Started background thread to enqueue {len(to_import)} subscriptions")
            else:
                _enqueue_subscriptions_async(to_import, user_id, site_name)
                logger.info(f"Synchronously enqueued {len(to_import)} subscriptions")
        else:
            logger.info("No new subscriptions to import")

        return {
            'total': len(to_import),
            'found': found_total,
            'selected': selected_total,
            'skipped': selected_total - len(to_import)
        }

    except Exception as e:
        logger.error(f"Failed to import subscriptions from {site_name}: {e}", exc_info=True)
        raise


def auto_import_missing_subscriptions(
    *,
    user_ids: Optional[List[int]] = None,
    site_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    resolved_user_ids = list(dict.fromkeys(user_ids or list_user_ids()))
    resolved_site_names = list(dict.fromkeys(site_names or get_enabled_runtime_import_sites()))

    summary = {
        'users': len(resolved_user_ids),
        'sites': len(resolved_site_names),
        'imported': 0,
        'skipped': 0,
        'failed': 0,
    }

    if not resolved_user_ids or not resolved_site_names:
        logger.info(
            "Skipped automatic subscription import: users=%s, sites=%s",
            len(resolved_user_ids),
            len(resolved_site_names),
        )
        return summary

    for user_id in resolved_user_ids:
        for site_name in resolved_site_names:
            try:
                result = import_user_subscriptions(
                    site_name,
                    user_id,
                    use_background_thread=False,
                    respect_manual_unsubscribe=True,
                )
                summary['imported'] += int(result.get('total') or 0)
                summary['skipped'] += int(result.get('skipped') or 0)
            except Exception as exc:
                summary['failed'] += 1
                logger.error(
                    "Automatic subscription import failed for user_id=%s site=%s: %s",
                    user_id,
                    site_name,
                    exc,
                    exc_info=True,
                )

    logger.info(
        "Automatic subscription import completed: users=%s, sites=%s, imported=%s, skipped=%s, failed=%s",
        summary['users'],
        summary['sites'],
        summary['imported'],
        summary['skipped'],
        summary['failed'],
    )
    return summary