from domains.system.infrastructure import logs as logs_module


def test_read_log_lines_can_page_from_stable_oldest_entries(monkeypatch, tmp_path):
    monkeypatch.setattr(logs_module, 'LOG_DIR', str(tmp_path))
    (tmp_path / 'app.log').write_text(
        '\n'.join(
            [
                '2026-07-15 10:00:00,000 INFO test: first',
                '2026-07-15 10:01:00,000 WARNING test: second',
                '2026-07-15 10:02:00,000 ERROR test: third',
            ]
        ),
        encoding='utf-8',
    )

    oldest, total, has_more = logs_module.LogService.read_log_lines(limit=2, newest_first=False)
    newest, _, _ = logs_module.LogService.read_log_lines(limit=2, newest_first=True)

    assert total == 3
    assert has_more is True
    assert [entry['message'] for entry in oldest] == ['first', 'second']
    assert [entry['message'] for entry in newest] == ['third', 'second']
