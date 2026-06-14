import json
import logging
import threading
from typing import Any

from domains.subscription.application.services.core.crud import subscription_crud_service
from domains.subscription.application.services.core.manage import subscription_manage_service
from domains.subscription.application.services.core.runtime_models import (
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
)
from domains.subscription.domain.models.subscription import Subscription
from infrastructure.database.session import get_session
from infrastructure.messaging.framework.producer import RedisStreamProducer
from infrastructure.messaging.models.message import Message
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.url import extract_top_level_domain
from infrastructure.site_runtimes.gateway import SiteRuntimeGateway
from infrastructure.site_runtimes.models import SiteRuntimeSnapshot
from infrastructure.site_runtimes.ports import get_runtime_gateway, get_runtime_snapshot
from shared_kernel.system import constants

logger = logging.getLogger(__name__)


class SubscriptionImportService:
    def __init__(self, session_factory=get_session, crud_service=None, manage_service=None):
        self.session_factory = session_factory
        self.crud_service = crud_service or subscription_crud_service
        self.manage_service = manage_service or subscription_manage_service

    @staticmethod
    def get_runtime_supported_sites(
        capability: str,
        snapshot: SiteRuntimeSnapshot | None = None,
    ) -> list[str]:
        snapshot = snapshot or get_runtime_snapshot()
        return sorted({
            registration.site_name
            for registration in snapshot.registrations
            if registration.capability == capability and registration.site_name
        })

    @staticmethod
    def get_enabled_runtime_import_sites() -> list[str]:
        return [
            site
            for site in SubscriptionImportService.get_runtime_supported_sites('import_subscriptions')
            if SiteCatalog.is_site_enabled(site=site)
        ]

    @staticmethod
    def _load_runtime_subscription_meta(
        url: str,
        gateway: SiteRuntimeGateway | None = None,
    ) -> SubscriptionMeta:
        from urllib.parse import urlparse
        domain = extract_top_level_domain(url)
        parsed_url = urlparse(url)
        payload = {
            'url': url,
            'domain': domain or parsed_url.netloc.lower().split(':')[0],
        }
        runtime_gateway = gateway or get_runtime_gateway()
        response = runtime_gateway.invoke(
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

    @staticmethod
    def _dedupe_import_items(subscriptions: list[SubscriptionImportItem]) -> list[SubscriptionImportItem]:
        seen_urls = set()
        result = []
        for sub in subscriptions:
            if not sub.url or sub.url in seen_urls:
                continue
            seen_urls.add(sub.url)
            result.append(sub)
        return result

    @staticmethod
    def _load_runtime_import_batch(
        site_name: str,
        *,
        cursor_payload: dict[str, Any] | None = None,
        limit: int | None = None,
        gateway: SiteRuntimeGateway | None = None,
    ) -> SubscriptionImportBatchResult:
        payload: dict[str, Any] = {}
        if cursor_payload:
            payload['cursor_payload'] = dict(cursor_payload)
        if limit is not None:
            payload['limit'] = limit

        runtime_gateway = gateway or get_runtime_gateway()
        response = runtime_gateway.invoke(
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
        batch.items = SubscriptionImportService._dedupe_import_items(batch.items)
        return batch

    @staticmethod
    def _load_runtime_import_items(site_name: str) -> list[SubscriptionImportItem]:
        items: list[SubscriptionImportItem] = []
        cursor_payload: dict[str, Any] | None = None

        while True:
            batch = SubscriptionImportService._load_runtime_import_batch(
                site_name,
                cursor_payload=cursor_payload,
            )
            items.extend(batch.items)
            if not batch.has_more:
                break
            cursor_payload = batch.cursor_payload

        return SubscriptionImportService._dedupe_import_items(items)

    def handle_subscribe_request(self, url: str, user_id: int) -> Subscription:
        existing_subscription = self.crud_service.get_active_user_subscription_by_url(user_id=user_id, url=url)
        if existing_subscription:
            return existing_subscription

        subscribe_info = self._load_runtime_subscription_meta(url)

        subscription = self.crud_service.get_subscription_by_url_and_name(url, subscribe_info.name)

        if subscription:
            self.manage_service.restore_subscription(subscription.id, user_id)
            return self.crud_service.get_subscription_by_id(subscription.id)

        subscription = self.manage_service.create_subscription(user_id, subscribe_info)
        return subscription

    def preview_user_subscriptions(
        self,
        site_name: str,
        user_id: int,
        *,
        cursor_payload: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        try:
            import_batch = self._load_runtime_import_batch(
                site_name,
                cursor_payload=cursor_payload,
                limit=limit,
            )
            subscriptions = import_batch.items

            logger.info('Found %s subscriptions from %s for preview', len(subscriptions), site_name)

            imported_url_map = self.crud_service.get_active_user_subscription_url_map(user_id)
            imported_count = 0

            preview_subscriptions = []
            for sub in subscriptions:
                data = sub.to_dict()
                is_imported = sub.url in imported_url_map
                data['is_imported'] = is_imported
                if is_imported:
                    data['subscription_id'] = imported_url_map[sub.url]
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

        except Exception as e:  # API boundary — re-raise after logging
            logger.error('Failed to preview subscriptions from %s: %s', site_name, e, exc_info=True)
            raise

    def _enqueue_subscriptions_async(self, subscriptions: list[SubscriptionImportItem], user_id: int, site_name: str):
        try:
            enqueued = 0
            producer = RedisStreamProducer()

            with self.session_factory() as session:
                for sub in subscriptions:
                    url = sub.url
                    try:
                        task = {
                            'url': url,
                            'name': sub.name,
                            'avatar': sub.avatar,
                            'user_id': user_id,
                        }
                        message = Message(body=json.dumps(task))
                        session.add(message)
                        session.flush()

                        dump_json = message.to_dict()
                        producer.send(constants.QUEUE_SUBSCRIBE, dump_json)
                        enqueued += 1

                    except (ConnectionError, OSError, ValueError, TypeError) as e:
                        logger.warning('Failed to enqueue subscription %s: %s', url, e)

                session.commit()

            logger.info('Enqueued %s/%s subscription tasks from %s', enqueued, len(subscriptions), site_name)

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error('Failed to enqueue subscriptions from %s: %s', site_name, e, exc_info=True)

    def import_user_subscriptions(
        self,
        site_name: str,
        user_id: int,
        selected_urls: list[str] | None = None,
        *,
        use_background_thread: bool = True,
        respect_manual_unsubscribe: bool = False,
    ) -> dict[str, Any]:
        try:
            if selected_urls is not None:
                subscriptions = self._dedupe_import_items([
                    SubscriptionImportItem(url=url)
                    for url in selected_urls
                    if url
                ])
                found_total = None
            else:
                subscriptions = self._load_runtime_import_items(site_name)
                found_total = len(subscriptions)
                logger.info('Found %s subscriptions from %s', found_total, site_name)
            selected_total = len(subscriptions)

            imported_url_map = self.crud_service.get_active_user_subscription_url_map(user_id)
            imported_urls = set(imported_url_map.keys())
            manually_unsubscribed_urls = (
                self.crud_service.get_deleted_user_subscription_urls(user_id)
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
                        target=self._enqueue_subscriptions_async,
                        args=(to_import, user_id, site_name),
                        daemon=True,
                    )
                    thread.start()
                    logger.info('Started background thread to enqueue %s subscriptions', len(to_import))
                else:
                    self._enqueue_subscriptions_async(to_import, user_id, site_name)
                    logger.info('Synchronously enqueued %s subscriptions', len(to_import))
            else:
                logger.info('No new subscriptions to import')

            return {
                'total': len(to_import),
                'found': found_total,
                'selected': selected_total,
                'skipped': selected_total - len(to_import),
            }

        except Exception as e:  # API boundary — re-raise after logging
            logger.error('Failed to import subscriptions from %s: %s', site_name, e, exc_info=True)
            raise

    def auto_import_missing_subscriptions(
        self,
        *,
        user_ids: list[int] | None = None,
        site_names: list[str] | None = None,
    ) -> dict[str, Any]:
        resolved_user_ids = list(dict.fromkeys(user_ids or self.manage_service.list_user_ids()))
        resolved_site_names = list(dict.fromkeys(site_names or self.get_enabled_runtime_import_sites()))

        summary = {
            'users': len(resolved_user_ids),
            'sites': len(resolved_site_names),
            'imported': 0,
            'skipped': 0,
            'failed': 0,
        }

        if not resolved_user_ids or not resolved_site_names:
            logger.info(
                'Skipped automatic subscription import: users=%s, sites=%s',
                len(resolved_user_ids),
                len(resolved_site_names),
            )
            return summary

        for user_id in resolved_user_ids:
            for site_name in resolved_site_names:
                try:
                    result = self.import_user_subscriptions(
                        site_name,
                        user_id,
                        use_background_thread=False,
                        respect_manual_unsubscribe=True,
                    )
                    summary['imported'] += int(result.get('total') or 0)
                    summary['skipped'] += int(result.get('skipped') or 0)
                except Exception as exc:  # auto-import boundary — count failure and continue
                    summary['failed'] += 1
                    logger.error(
                        'Automatic subscription import failed for user_id=%s site=%s: %s',
                        user_id,
                        site_name,
                        exc,
                        exc_info=True,
                    )

        logger.info(
            'Automatic subscription import completed: users=%s, sites=%s, imported=%s, skipped=%s, failed=%s',
            summary['users'],
            summary['sites'],
            summary['imported'],
            summary['skipped'],
            summary['failed'],
        )
        return summary


subscription_import_service = SubscriptionImportService()
get_runtime_supported_sites = subscription_import_service.get_runtime_supported_sites
get_enabled_runtime_import_sites = subscription_import_service.get_enabled_runtime_import_sites
handle_subscribe_request = subscription_import_service.handle_subscribe_request
preview_user_subscriptions = subscription_import_service.preview_user_subscriptions
import_user_subscriptions = subscription_import_service.import_user_subscriptions
auto_import_missing_subscriptions = subscription_import_service.auto_import_missing_subscriptions
