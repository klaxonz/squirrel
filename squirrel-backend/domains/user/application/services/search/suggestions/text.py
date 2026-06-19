from infrastructure.search.query import parse_search_query


def normalize_query(value: str | None) -> str:
    return ' '.join(str(value or '').strip().split())


def extract_suggestion_term(query: str | None) -> str:
    normalized_query = normalize_query(query).lower()
    if not normalized_query:
        return ''

    parsed_query = parse_search_query(normalized_query)
    preferred_groups = (
        parsed_query.get('title'),
        parsed_query.get('subscription'),
        parsed_query.get('creator'),
        parsed_query.text_terms,
        parsed_query.get('domain'),
        parsed_query.get('description'),
        parsed_query.get('url'),
    )

    for group in preferred_groups:
        if group:
            return group[-1]

    return normalized_query


def score_candidate(value: str, query: str) -> int:
    lowered_value = value.lower()
    if lowered_value == query:
        return 0
    if lowered_value.startswith(query):
        return 1
    return 2
