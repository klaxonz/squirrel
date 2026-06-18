import json
import logging

from fastapi import APIRouter, Depends, Query

from domains.subscription.application.services.core.import_service import subscription_import_service
from domains.subscription.interfaces.dto.request.subscription import ImportSubscriptionsRequest
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from infrastructure.http import response

from .site_imports import get_enabled_import_sites, get_supported_site_set, normalize_site_name

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/import/sites")
def get_supported_sites(
        current_user: User = Depends(get_current_user),
):
    """Get list of sites supported for import

    Returns:
        List of supported sites

    """
    supported_sites = subscription_import_service.get_plugin_supported_sites("import_subscriptions")
    enabled_sites = get_enabled_import_sites(supported_sites)

    return response.success({
        "sites": enabled_sites,
    })


@router.get("/import/{site}/preview")
def preview_subscriptions(
    site: str,
    cursor: str | None = Query(None, description="Pagination cursor JSON"),
    limit: int = Query(50, ge=1, le=200, description="Preview page size"),
    current_user: User = Depends(get_current_user),
    ):
    """Preview user's subscriptions at a given site (without actually importing)

    Args:
        site: Site name

    Returns:
        Preview result

    """
    try:
        supported_sites = subscription_import_service.get_plugin_supported_sites("import_subscriptions")
        supported_site_set = get_supported_site_set(supported_sites)
        normalized_site = normalize_site_name(site)
        enabled_sites = get_enabled_import_sites(supported_sites)

        if normalized_site not in supported_site_set:
            return response.param_error(f"不支持的站点: {site}，支持的站点: {', '.join(supported_sites)}")
        if normalized_site not in enabled_sites:
            return response.param_error(f"站点已禁用，无法预览订阅: {site}")

        cursor_payload = None
        if cursor:
            try:
                parsed_cursor = json.loads(cursor)
            except json.JSONDecodeError as exc:
                raise ValueError(f"无效的预览游标: {exc.msg}") from exc
            if not isinstance(parsed_cursor, dict):
                raise ValueError("无效的预览游标: 必须为 JSON object")
            cursor_payload = parsed_cursor

        logger.info("User %s previewing subscriptions from %s", current_user.id, normalized_site)

        preview_result = subscription_import_service.preview_user_subscriptions(
            normalized_site,
            current_user.id,
            cursor_payload=cursor_payload,
            limit=limit,
        )

        return response.success(preview_result)

    except ValueError as e:
        logger.error("Invalid request for site %s: %s", site, e)
        return response.param_error(str(e))
    except Exception as e:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to preview subscriptions from %s: %s", site, e)
        return response.server_error(f"预览失败: {e!s}")


@router.post("/import/{site}")
def import_subscriptions(
    site: str,
    req: ImportSubscriptionsRequest | None = None,
    current_user: User = Depends(get_current_user),
    ):
    """Import all user subscriptions from a specified site

    Args:
        site: Site name (dynamically supports all registered sites)

    Returns:
        Import result statistics

    """
    try:
        supported_sites = subscription_import_service.get_plugin_supported_sites("import_subscriptions")
        supported_site_set = get_supported_site_set(supported_sites)
        normalized_site = normalize_site_name(site)
        enabled_sites = get_enabled_import_sites(supported_sites)

        if normalized_site not in supported_site_set:
            return response.param_error(f"不支持的站点: {site}，支持的站点: {', '.join(supported_sites)}")
        if normalized_site not in enabled_sites:
            return response.param_error(f"站点已禁用，无法导入订阅: {site}")

        logger.info("User %s importing subscriptions from %s", current_user.id, normalized_site)

        selected_urls = req.subscription_urls if req else None
        import_result = subscription_import_service.import_user_subscriptions(
            normalized_site,
            current_user.id,
            selected_urls=selected_urls,
        )

        return response.success({
            "site": normalized_site,
            "total": import_result["total"],
            "found": import_result["found"],
            "selected": import_result["selected"],
            "skipped": import_result["skipped"],
        })

    except ValueError as e:
        logger.error("Invalid request for site %s: %s", site, e)
        return response.param_error(str(e))
    except Exception as e:
        # API boundary -- convert to HTTP error response
        logger.exception("Failed to import subscriptions from %s: %s", site, e)
        return response.server_error(f"导入失败: {e!s}")
