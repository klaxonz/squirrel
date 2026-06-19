from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from application.app import request_validation_error_handler


def test_request_validation_errors_use_response_envelope():
    app = FastAPI(exception_handlers={RequestValidationError: request_validation_error_handler})

    @app.get('/items')
    def list_items(page: int = Query(1, ge=1)):
        return {'page': page}

    response = TestClient(app).get('/items?page=0')

    assert response.status_code == 400
    assert response.json() == {'code': 400, 'msg': '请求参数错误', 'data': None}
