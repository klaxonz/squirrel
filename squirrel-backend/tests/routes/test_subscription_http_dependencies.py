import ast
from pathlib import Path

HTTP_DIR = Path(__file__).resolve().parents[2] / 'domains' / 'subscription' / 'interfaces' / 'http'
FORBIDDEN_SINGLETONS = {
    'subscription_crud_service',
    'subscription_import_service',
    'subscription_list_service',
    'subscription_manage_service',
    'scheduler',
}


def test_subscription_http_routes_use_dependency_providers_for_application_services():
    offenders = []

    for path in HTTP_DIR.glob('*.py'):
        if path.name in {'__init__.py', 'dependencies.py'}:
            continue

        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names = {alias.name for alias in node.names}
                forbidden = sorted(imported_names & FORBIDDEN_SINGLETONS)
                if forbidden:
                    offenders.append(f'{path.name}: {", ".join(forbidden)}')

    assert offenders == []
