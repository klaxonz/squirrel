"""Tests for the shared domain exception hierarchy.

Locks in the HTTP-status mapping and message conventions that
``application.app.domain_error_handler`` relies on.
"""

import pytest

from shared_kernel.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


@pytest.mark.parametrize(
    ('exc_cls', 'expected_status'),
    [
        (ValidationError, 400),
        (AuthenticationError, 401),
        (ForbiddenError, 403),
        (NotFoundError, 404),
        (ConflictError, 409),
    ],
)
def test_each_subclass_maps_to_expected_http_status(exc_cls, expected_status):
    assert exc_cls().http_status == expected_status
    # ``code`` mirrors ErrorCode so the response body stays consistent.
    assert exc_cls().code == expected_status


def test_all_subclasses_inherit_from_domain_error():
    for cls in (ValidationError, NotFoundError, ConflictError, ForbiddenError, AuthenticationError):
        assert issubclass(cls, DomainError)


def test_not_found_builds_message_from_resource_and_identifier():
    assert NotFoundError('用户').message == '用户 不存在'
    assert NotFoundError(resource='Playlist', identifier=5).message == "Playlist 5 不存在"
    assert NotFoundError().message == '资源不存在'


def test_custom_message_overrides_default():
    assert ConflictError('邮箱已被注册').message == '邮箱已被注册'
    assert ValidationError('end_time must be greater than or equal to start_time').message == (
        'end_time must be greater than or equal to start_time'
    )


def test_domain_error_is_catchable_as_exception():
    with pytest.raises(DomainError):
        raise NotFoundError('Video')
    # And as the base builtin Exception (so middleware that catches Exception still sees it).
    with pytest.raises(Exception):
        raise ForbiddenError('nope')


def test_optional_details_payload_is_preserved():
    err = ValidationError('bad', details={'field': 'url'})
    assert err.details == {'field': 'url'}
    assert err.message == 'bad'
