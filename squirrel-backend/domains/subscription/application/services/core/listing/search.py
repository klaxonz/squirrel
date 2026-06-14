from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from domains.subscription.domain.models.subscription import Subscription
from infrastructure.search.query import escape_ilike, normalize_subscription_type_term, parse_search_query


def contains(column: Any, term: str) -> ColumnElement[bool]:
    return column.ilike(f'%{escape_ilike(term)}%')


def build_subscription_search_clauses(query: str | None) -> list[Any]:
    parsed_query = parse_search_query(query)
    if not parsed_query.has_terms:
        return []

    clauses: list[Any] = []

    for term in parsed_query.text_terms:
        clauses.append(
            or_(
                contains(Subscription.name, term),
                contains(Subscription.description, term),
                contains(Subscription.url, term),
            ),
        )

    for term in parsed_query.get('subscription'):
        clauses.append(
            or_(
                contains(Subscription.name, term),
                contains(Subscription.description, term),
                contains(Subscription.url, term),
            ),
        )

    for term in parsed_query.get('url'):
        clauses.append(contains(Subscription.url, term))

    for term in parsed_query.get('domain'):
        clauses.append(contains(Subscription.url, term))

    for term in parsed_query.get('description'):
        clauses.append(contains(Subscription.description, term))

    for term in parsed_query.get('title'):
        clauses.append(contains(Subscription.name, term))

    for term in parsed_query.get('type'):
        normalized_type = normalize_subscription_type_term(term)
        if normalized_type:
            clauses.append(Subscription.type == normalized_type)

    return clauses
