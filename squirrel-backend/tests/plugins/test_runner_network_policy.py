from pathlib import Path
import sys

RUNNER_SRC = Path(__file__).resolve().parents[3] / 'squirrel-plugin-runner' / 'src'
sys.path.insert(0, str(RUNNER_SRC))

from squirrel_plugin_runner.runtime_bridge import (  # noqa: E402
    host_is_allowed,
    normalize_network_policy,
)


def test_normalize_network_policy_denies_network_when_permission_missing():
    policy = normalize_network_policy(None, granted_permissions=[])

    assert policy['mode'] == 'deny_all'
    assert host_is_allowed(policy, 'example.com') is False


def test_normalize_network_policy_allows_suffix_matches():
    policy = normalize_network_policy(
        {
            'mode': 'allow_list',
            'allow_hosts': ['youtube.com'],
            'deny_hosts': [],
        },
        granted_permissions=['network:http'],
    )

    assert host_is_allowed(policy, 'youtube.com') is True
    assert host_is_allowed(policy, 'api.youtube.com') is True
    assert host_is_allowed(policy, 'example.com') is False


def test_normalize_network_policy_denies_explicit_hosts_first():
    policy = normalize_network_policy(
        {
            'mode': 'allow_list',
            'allow_hosts': ['youtube.com'],
            'deny_hosts': ['api.youtube.com'],
        },
        granted_permissions=['network:http'],
    )

    assert host_is_allowed(policy, 'api.youtube.com') is False
    assert host_is_allowed(policy, 'www.youtube.com') is True
