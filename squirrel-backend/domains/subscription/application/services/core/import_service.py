import logging
from typing import Any

from sqlalchemy.exc import IntegrityError

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.import_errors import SubscriptionImportError
from domains.subscription.application.services.core.manage import SubscriptionManageService
from domains.subscription.application.services.core.runtime_models import (
    SubscriptionImportBatchResult,
    SubscriptionImportItem,
    SubscriptionMeta,
)
from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.domain.models.subscription import Subscription, build_subscription_canonical_key
from infrastructure.database.session import get_session
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_catalog.url import extract_top_level_domain
from infrastructure.site_registry.registry import SiteRegistry, get_site_registry
from shared_kernel.domain.exceptions import ValidationError
from sites.crawl import SiteError

logger = logging.getLogger(__name__)


class SubscriptionImportService:
    def __init__(
        self,
        *,
        registry: SiteRegistry | None = None,
        session_factory=get_session,
        crud_service=None,
        manage_service=None,
        crawl_tasks=None,
    ):
        self._registry = registry or get_site_registry()
        self.session_factory = session_factory
        self.crud_service = crud_service or SubscriptionCrudService(session_factory)
        self.manage_service = manage_service or SubscriptionManageService(
            session_factory=session_factory,
            crud_service=self.crud_service,
            lifecycle=SubscriptionSyncLifecycle(session_factory=session_factory),
        )
        self._crawl_tasks = crawl_tasks or crawl_task_service

    @staticmethod
    def get_supported_import_sites(
        capability: str,
    ) -> list[str]:
        return sorted(get_site_registry().get_supported_sites(capability))

    @staticmethod
    def get_enabled_import_sites() -> list[str]:
        return [
            site
            for site in SubscriptionImportService.get_supported_import_sites('import_subscriptions')
            if SiteCatalog.is_site_enabled(site=site)
        ]

    def _load_site_subscription_meta(
        self,
        url: str,
    ) -> SubscriptionMeta:

        domain = extract_top_level_domain(url)
        slug = self._registry.find_site_by_domain(domain or None)
        if not slug:
            raise ValidationError(f'No subscription route found for url: {url}')
        try:
            meta = self._registry.get_site_runtime(slug).resolve_subscription(url, domain=domain or None)
        except SiteError as exc:
            raise self._site_error_to_import_error(exc) from exc

        return SubscriptionMeta.from_dict(meta.to_dict())

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

    def _load_site_import_batch(
        self,
        site_name: str,
        *,
        cursor_payload: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> SubscriptionImportBatchResult:
        try:
            batch = self._registry.get_site_runtime(site_name).import_subscriptions(
                cursor_payload=cursor_payload,
                limit=limit,
            )
        except SiteError as exc:
            raise self._site_error_to_import_error(exc) from exc

        domain_batch = SubscriptionImportBatchResult.from_dict(batch.to_dict())
        domain_batch.items = SubscriptionImportService._dedupe_import_items(domain_batch.items)
        return domain_batch

    @staticmethod
    def _site_error_to_import_error(exc: SiteError) -> SubscriptionImportError:
        return SubscriptionImportError(
            str(exc),
            retryable=bool(exc.retryable),
            error_type=str(exc.category.value),
            retry_after_seconds=getattr(exc, 'retry_after', None),
        )

    def _load_site_import_items(self, site_name: str) -> list[SubscriptionImportItem]:
        items: list[SubscriptionImportItem] = []
        cursor_payload: dict[str, Any] | None = None

        while True:
            batch = self._load_site_import_batch(
                site_name,
                cursor_payload=cursor_payload,
            )
            items.extend(batch.items)
            if not batch.has_more:
                break
            cursor_payload = batch.cursor_payload

        return SubscriptionImportService._dedupe_import_items(items)

    def handle_subscribe_request(
        self,
        url: str,
        user_id: int,
        *,
        expected_intent_version: int | None = None,
    ) -> Subscription:
        existing_subscription = self.crud_service.get_active_user_subscription_by_url(user_id=user_id, url=url)
        if existing_subscription:
            return existing_subscription

        subscribe_info = self._load_site_subscription_meta(url)

        subscription = self.crud_service.get_subscription_by_url(url)

        if subscription:
            self.manage_service.restore_subscription(
                subscription.id,
                user_id,
                expected_intent_version=expected_intent_version,
            )
            return self.crud_service.get_subscription_by_id(subscription.id)

        subscription = self.manage_service.create_subscription(
            user_id,
            subscribe_info,
            expected_intent_version=expected_intent_version,
        )
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
            import_batch = self._load_site_import_batch(
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
                'total': import_batch.total_available
                if import_batch.total_available is not None
                else len(subscriptions),
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

    def _enqueue_subscription_tasks(
        self,
        subscriptions: list[SubscriptionImportItem],
        user_id: int,
        site_name: str,
    ) -> int:
        enqueued = 0
        intent_versions = self.crud_service.get_user_subscription_intent_versions(
            user_id,
            [sub.url for sub in subscriptions],
        )
        for sub in subscriptions:
            expected_intent_version = intent_versions.get(sub.url, 0)
            payload = {
                **sub.to_dict(),
                'user_id': user_id,
                'site_name': site_name,
                'expected_intent_version': expected_intent_version,
            }
            dedupe_key = self.build_import_dedupe_key(
                user_id,
                sub.url,
                expected_intent_version=expected_intent_version,
            )
            try:
                self._crawl_tasks.create_job_with_task(
                    job_type='subscription_import',
                    source_type='scheduled',
                    site=site_name,
                    task_type='subscription_import',
                    payload=payload,
                    priority='normal',
                    dedupe_key=dedupe_key,
                    max_attempts=3,
                )
                enqueued += 1
            except IntegrityError as exc:
                constraint_name = getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None)
                if constraint_name not in {None, 'uq_crawl_task_dedupe_key'} or not (
                    self._crawl_tasks.has_task_with_dedupe_key(dedupe_key)
                ):
                    raise
                # A unique dedupe-key collision means the same durable task is already pending.
                logger.debug('Subscription import task already queued: user_id=%s url=%s', user_id, sub.url)
                continue
        logger.info('Enqueued %s/%s durable subscription tasks from %s', enqueued, len(subscriptions), site_name)
        return enqueued

    @staticmethod
    def build_import_dedupe_key(
        user_id: int,
        url: str,
        *,
        expected_intent_version: int = 0,
    ) -> str:
        digest = build_subscription_canonical_key(url)
        return f'dedupe:subscription_import:{user_id}:{digest}:{expected_intent_version}'

    def process_import_payload(self, payload: dict[str, Any]) -> Subscription:
        url = str(payload.get('url') or '').strip()
        user_id = int(payload['user_id'])
        if not url:
            raise ValidationError('Subscription import URL is required')
        expected_intent_version = int(payload.get('expected_intent_version', 0))

        existing = self.crud_service.get_active_user_subscription_by_url(user_id=user_id, url=url)
        if existing:
            return existing

        global_subscription = self.crud_service.get_subscription_by_url(url)
        if global_subscription:
            self.manage_service.restore_subscription(
                global_subscription.id,
                user_id,
                expected_intent_version=expected_intent_version,
            )
            return self.crud_service.get_subscription_by_id(global_subscription.id)

        name = str(payload.get('name') or '').strip()
        if name:
            subscribe_info = SubscriptionMeta(
                id=str(payload.get('external_id') or url),
                name=name,
                avatar=payload.get('avatar'),
                url=url,
            )
            return self.manage_service.create_subscription(
                user_id,
                subscribe_info,
                expected_intent_version=expected_intent_version,
            )
        return self.handle_subscribe_request(
            url,
            user_id,
            expected_intent_version=expected_intent_version,
        )

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
                subscriptions = self._dedupe_import_items(
                    [SubscriptionImportItem(url=url) for url in selected_urls if url]
                )
                found_total = None
            else:
                subscriptions = self._load_site_import_items(site_name)
                found_total = len(subscriptions)
                logger.info('Found %s subscriptions from %s', found_total, site_name)
            selected_total = len(subscriptions)

            imported_url_map = self.crud_service.get_active_user_subscription_url_map(user_id)
            imported_urls = set(imported_url_map.keys())
            manually_unsubscribed_urls = (
                self.crud_service.get_deleted_user_subscription_urls(user_id) if respect_manual_unsubscribe else set()
            )
            to_import = [
                s for s in subscriptions if s.url not in imported_urls and s.url not in manually_unsubscribed_urls
            ]

            enqueued = 0
            if to_import:
                enqueued = self._enqueue_subscription_tasks(to_import, user_id, site_name)
                logger.info(
                    'Persisted %s subscription import tasks (background_hint=%s)',
                    enqueued,
                    use_background_thread,
                )
            else:
                logger.info('No new subscriptions to import')

            return {
                'total': enqueued,
                'found': found_total,
                'selected': selected_total,
                'skipped': selected_total - enqueued,
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
        resolved_site_names = list(dict.fromkeys(site_names or self.get_enabled_import_sites()))

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
get_supported_import_sites = subscription_import_service.get_supported_import_sites
get_enabled_import_sites = subscription_import_service.get_enabled_import_sites
handle_subscribe_request = subscription_import_service.handle_subscribe_request
preview_user_subscriptions = subscription_import_service.preview_user_subscriptions
import_user_subscriptions = subscription_import_service.import_user_subscriptions
auto_import_missing_subscriptions = subscription_import_service.auto_import_missing_subscriptions
process_import_payload = subscription_import_service.process_import_payload
