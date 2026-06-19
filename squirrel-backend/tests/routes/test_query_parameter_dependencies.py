import ast
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

ROUTE_FUNCTIONS = {
    'application/routes/logs.py': {'query_logs'},
    'domains/rss/interfaces/http/entries.py': {'list_rss_entries'},
    'domains/rss/interfaces/http/sync.py': {'start_rss_sync'},
    'domains/subscription/interfaces/http/basic.py': {'list_subscriptions'},
    'domains/subscription/interfaces/http/imports.py': {'preview_subscriptions'},
    'domains/user/interfaces/http/search.py': {'get_search_suggestions'},
    'domains/video/interfaces/http/history.py': {'get_history_list'},
    'domains/video/interfaces/http/listing.py': {'get_videos'},
    'domains/video/interfaces/http/random.py': {'get_random_video'},
    'infrastructure/scheduling/routes/tasks.py': {'get_scheduled_tasks'},
}


def _uses_query(default: ast.AST | None) -> bool:
    return (
        isinstance(default, ast.Call)
        and isinstance(default.func, ast.Name)
        and default.func.id == 'Query'
    )


def test_multi_parameter_query_routes_use_dependency_objects():
    offenders = []

    for relative_path, function_names in ROUTE_FUNCTIONS.items():
        path = BACKEND_DIR / relative_path
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name not in function_names:
                continue

            positional_defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + node.args.defaults
            defaults = [*positional_defaults, *node.args.kw_defaults]
            if any(_uses_query(default) for default in defaults):
                offenders.append(f'{relative_path}:{node.name}')

    assert offenders == []
