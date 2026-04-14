from pathlib import Path


VERSIONS_DIR = Path(__file__).resolve().parents[1] / 'alembic' / 'versions'


def test_playlist_tables_are_covered_by_alembic_migrations():
    migration_sources = [
        path.read_text(encoding='utf-8')
        for path in VERSIONS_DIR.glob('*.py')
        if path.name != '__init__.py'
    ]
    combined_source = '\n'.join(migration_sources)

    assert "op.create_table(\n        'playlist'" in combined_source
    assert "op.create_table(\n        'playlist_item'" in combined_source
