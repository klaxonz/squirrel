import logging

from fastapi import APIRouter, Query

from common.response import error, success
from services.site_catalog.cookiecloud import CookieCloudSyncError, sync_cookiecloud_to_site_files

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('/cookiecloud/sync')
def sync_cookies_from_cookiecloud(site_name: str | None = Query(None)):
    try:
        data = sync_cookiecloud_to_site_files(site_slug=site_name)
        return success(data, msg='CookieCloud sync completed')
    except CookieCloudSyncError as exc:
        return error(str(exc))
    except Exception as exc:
        logger.exception('CookieCloud sync failed: %s', exc)
        return error(f'CookieCloud sync failed: {exc}')
