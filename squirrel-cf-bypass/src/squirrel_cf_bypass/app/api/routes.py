from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import Response

router = APIRouter()


@router.get('/health')
async def health(request: Request):
    return request.app.state.bypass_service.health_payload()


@router.post('/cache/clear')
async def clear_cache(request: Request):
    await request.app.state.bypass_service.clear_runtime_state()
    return {'status': 'ok'}


@router.get('/html')
async def html(request: Request, url: str):
    result = await request.app.state.bypass_service.fetch_html(url)
    if result is None:
        raise HTTPException(status_code=502, detail='Failed to bypass Cloudflare protection')
    return HTMLResponse(
        content=result.html,
        status_code=result.status_code,
        headers={
            'x-cf-bypasser-cookies': str(len(result.cookies)),
            'x-cf-bypasser-user-agent': result.user_agent,
            'x-cf-bypasser-final-url': result.final_url,
        },
    )


@router.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'])
async def mirror(request: Request, path: str):
    headers = {key.lower(): value for key, value in request.headers.items()}
    if 'x-hostname' not in headers:
        raise HTTPException(status_code=400, detail='x-hostname header is required')

    body = await request.body()
    result = await request.app.state.bypass_service.mirror_request(
        method=request.method,
        path='/' + path,
        query_string=request.url.query,
        headers=headers,
        body=body,
    )
    return Response(content=result.body, status_code=result.status_code, headers=result.headers)
