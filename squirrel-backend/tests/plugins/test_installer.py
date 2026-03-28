from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginManifest, PluginSiteManifest, PluginCapability
from plugins.installer import PluginInstallPlan, PluginInstaller


def test_provision_runtime_environment_creates_venv_and_installs_runner_sdk_and_plugin(monkeypatch, tmp_path):
    installer = PluginInstaller(base_dir=tmp_path / 'plugin_runtime_v2')
    package_path = tmp_path / 'plugin.zip'
    package_path.write_text('zip-placeholder', encoding='utf-8')

    install_path = tmp_path / 'installed-plugin'
    install_path.mkdir()
    (install_path / 'pyproject.toml').write_text('[project]\nname = "sample-plugin"\nversion = "0.1.0"\n', encoding='utf-8')

    plan = PluginInstallPlan(
        plugin_id='sample',
        version='0.1.0',
        package_path=package_path,
        staging_path=tmp_path / 'staging' / 'plugin.zip',
        install_path=install_path,
        runtime_path=tmp_path / 'runtime' / 'sample' / '0.1.0',
        entrypoint='sample_runtime:get_plugin_runtime',
        checksum_sha256='deadbeef',
        manifest=PluginManifest(
            plugin_id='sample',
            version='0.1.0',
            capabilities=[PluginCapability(name='echo')],
            sites=[PluginSiteManifest(site_name='sample', domains=['sample.test'])],
        ),
    )

    created_paths = []
    installed_targets = []

    class _FakeEnvBuilder:
        def __init__(self, with_pip=False, clear=False):
            self.with_pip = with_pip
            self.clear = clear

        def create(self, env_dir):
            env_path = Path(env_dir)
            created_paths.append(env_path)
            (env_path / 'Scripts').mkdir(parents=True, exist_ok=True)
            (env_path / 'Scripts' / 'python.exe').write_text('', encoding='utf-8')

    monkeypatch.setattr('plugins.installer.venv.EnvBuilder', _FakeEnvBuilder)
    monkeypatch.setattr(
        installer,
        '_run_pip_install',
        lambda python_exec, target: installed_targets.append((Path(python_exec), Path(target))),
    )

    runtime_env_path, runtime_python = installer.provision_runtime_environment(plan)

    assert created_paths == [plan.runtime_path]
    assert runtime_env_path == plan.runtime_path
    assert runtime_python == plan.runtime_path / 'Scripts' / 'python.exe'
    assert [target.name for _, target in installed_targets] == [
        'squirrel-sdk',
        'squirrel-plugin-runner',
        'installed-plugin',
    ]
