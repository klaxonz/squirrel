import logging

from fastapi import APIRouter

from shared_kernel.application.response import error, success

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post('/youtube/oauth/setup')
def setup_youtube_oauth():
    try:
        from infrastructure.site_catalog.youtube_oauth import setup_oauth_via_daemon
        state = setup_oauth_via_daemon(timeout_seconds=60.0)
        return success({
            'status': state.status,
            'verification_url': state.verification_url,
            'user_code': state.user_code,
            'account': {
                'name': state.account.name if state.account else None,
                'email': state.account.email if state.account else None,
                'avatar': state.account.avatar if state.account else None,
            } if state.account or state.status == 'authenticated' else None,
            'error': state.error,
        })
    except Exception as exc:
        logger.exception('YouTube OAuth setup failed: %s', exc)
        return error(f'OAuth setup failed: {exc}')


@router.get('/youtube/oauth/status')
def get_youtube_oauth_status():
    try:
        from infrastructure.site_catalog.youtube_oauth import poll_oauth_status_via_daemon
        state = poll_oauth_status_via_daemon(timeout_seconds=10.0)
        return success({
            'status': state.status,
            'verification_url': state.verification_url,
            'user_code': state.user_code,
            'account': {
                'name': state.account.name if state.account else None,
                'email': state.account.email if state.account else None,
                'avatar': state.account.avatar if state.account else None,
            } if state.account else None,
            'error': state.error,
        })
    except Exception as exc:
        logger.exception('YouTube OAuth status check failed: %s', exc)
        return error(f'OAuth status query failed: {exc}')


@router.delete('/youtube/oauth')
def revoke_youtube_oauth():
    try:
        from infrastructure.site_catalog.youtube_oauth import revoke_oauth_via_daemon
        ok = revoke_oauth_via_daemon(timeout_seconds=30.0)
        return success({'revoked': ok}, msg='YouTube authorization revoked' if ok else 'Revocation failed')
    except Exception as exc:
        logger.exception('YouTube OAuth revoke failed: %s', exc)
        return error(f'Authorization revocation failed: {exc}')
