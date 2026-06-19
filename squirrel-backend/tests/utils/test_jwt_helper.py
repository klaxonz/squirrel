import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.auth import jwt as jwt_helper


def test_should_persist_auth_cookie_defaults_legacy_tokens_to_persistent():
    token = jwt_helper.create_access_token({'sub': '7'})

    assert jwt_helper.should_persist_auth_cookie(token) is True


def test_should_persist_auth_cookie_respects_remember_flag():
    remembered = jwt_helper.create_access_token({'sub': '7', jwt_helper.REMEMBER_ME_CLAIM: True})
    session_only = jwt_helper.create_access_token({'sub': '7', jwt_helper.REMEMBER_ME_CLAIM: False})

    assert jwt_helper.should_persist_auth_cookie(remembered) is True
    assert jwt_helper.should_persist_auth_cookie(session_only) is False
