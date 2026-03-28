from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import venv
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.config import settings

from .runtime_models import PluginManifest


class PluginPackageValidationError(ValueError):
    """Raised when a plugin package fails validation."""


@dataclass
class PluginInstallPlan:
    plugin_id: str
    version: str
    package_path: Path
    staging_path: Path
    install_path: Path
    runtime_path: Path
    data_path: Path
    entrypoint: str
    checksum_sha256: str
    manifest: PluginManifest
    replace_existing: bool = False


class PluginInstaller:
    """Build install plans for runtime V2 plugin packages."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or (settings.config_dir / 'plugin_runtime_v2')
        self._packages_dir = self._base_dir / 'packages'
        self._install_root = self._base_dir / 'installs'
        self._runtime_root = self._base_dir / 'runtime'
        self._data_root = self._base_dir / 'data'
        for path in (self._packages_dir, self._install_root, self._runtime_root, self._data_root):
            path.mkdir(parents=True, exist_ok=True)

    def compute_checksum(self, package_path: Path) -> str:
        digest = hashlib.sha256()
        with package_path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def validate_entrypoint(self, entrypoint: str) -> None:
        module_name, separator, attr_name = entrypoint.partition(':')
        if not separator or not module_name or not attr_name:
            raise PluginPackageValidationError('Plugin entrypoint must look like module.path:factory_name')

    def validate_manifest(self, manifest: PluginManifest) -> None:
        if not manifest.plugin_id:
            raise PluginPackageValidationError('Plugin manifest must include plugin_id')
        if not manifest.version:
            raise PluginPackageValidationError('Plugin manifest must include version')
        if not manifest.capabilities:
            raise PluginPackageValidationError('Plugin manifest must declare at least one capability')
        if not manifest.sites:
            raise PluginPackageValidationError('Plugin manifest must declare at least one site')

    def build_install_plan(
        self,
        package_path: Path | str,
        manifest: PluginManifest,
        entrypoint: str,
        replace_existing: bool = False,
    ) -> PluginInstallPlan:
        package = Path(package_path).resolve()
        if not package.exists():
            raise PluginPackageValidationError(f'Plugin package not found: {package}')

        self.validate_manifest(manifest)
        self.validate_entrypoint(entrypoint)
        checksum = self.compute_checksum(package)
        package_name = package.name

        staging_path = self._packages_dir / manifest.plugin_id / manifest.version / package_name
        install_path = self._install_root / manifest.plugin_id / manifest.version
        runtime_path = self._runtime_root / manifest.plugin_id / manifest.version
        data_path = self._data_root / manifest.plugin_id / manifest.version
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        install_path.mkdir(parents=True, exist_ok=True)
        runtime_path.mkdir(parents=True, exist_ok=True)
        data_path.mkdir(parents=True, exist_ok=True)

        return PluginInstallPlan(
            plugin_id=manifest.plugin_id,
            version=manifest.version,
            package_path=package,
            staging_path=staging_path,
            install_path=install_path,
            runtime_path=runtime_path,
            data_path=data_path,
            entrypoint=entrypoint,
            checksum_sha256=checksum,
            manifest=manifest,
            replace_existing=replace_existing,
        )

    def stage_distribution(self, plan: PluginInstallPlan) -> Path:
        if plan.staging_path.resolve() != plan.package_path.resolve():
            shutil.copy2(plan.package_path, plan.staging_path)
        if zipfile.is_zipfile(plan.staging_path):
            if plan.install_path.exists():
                shutil.rmtree(plan.install_path)
            plan.install_path.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(plan.staging_path, 'r') as archive:
                archive.extractall(plan.install_path)
        return plan.staging_path

    def provision_runtime_environment(self, plan: PluginInstallPlan) -> tuple[Path, Path]:
        runtime_env_path = plan.runtime_path
        if runtime_env_path.exists():
            shutil.rmtree(runtime_env_path)
        plan.data_path.mkdir(parents=True, exist_ok=True)

        builder = venv.EnvBuilder(with_pip=True, clear=True)
        builder.create(runtime_env_path)

        runtime_python = self._resolve_runtime_python(runtime_env_path)
        self._run_pip_install(runtime_python, self._sdk_package_dir())
        self._run_pip_install(runtime_python, self._runner_package_dir())
        self._run_pip_install(runtime_python, self._plugin_install_target(plan))
        return runtime_env_path, runtime_python

    def remove_runtime_environment(self, runtime_env_path: Path | str | None) -> None:
        if not runtime_env_path:
            return
        env_path = Path(runtime_env_path)
        if env_path.exists():
            shutil.rmtree(env_path)

    def remove_installation(self, install_path: Path | str | None) -> None:
        if not install_path:
            return
        path = Path(install_path)
        if path.exists():
            shutil.rmtree(path)

    def _resolve_runtime_python(self, runtime_env_path: Path) -> Path:
        if sys.platform == 'win32':
            return runtime_env_path / 'Scripts' / 'python.exe'
        return runtime_env_path / 'bin' / 'python'

    def _repo_root(self) -> Path:
        return settings.base_dir.parent

    def _sdk_package_dir(self) -> Path:
        sdk_dir = self._repo_root() / 'squirrel-sdk'
        if not sdk_dir.exists():
            raise PluginPackageValidationError(f'SDK package path not found: {sdk_dir}')
        return sdk_dir

    def _runner_package_dir(self) -> Path:
        runner_dir = self._repo_root() / 'squirrel-plugin-runner'
        if not runner_dir.exists():
            raise PluginPackageValidationError(f'Plugin runner package path not found: {runner_dir}')
        return runner_dir

    def _plugin_install_target(self, plan: PluginInstallPlan) -> Path:
        pyproject_path = plan.install_path / 'pyproject.toml'
        return plan.install_path if pyproject_path.exists() else plan.staging_path

    def _run_pip_install(self, python_executable: Path, target: Path) -> None:
        subprocess.run(
            [str(python_executable), '-m', 'pip', 'install', str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
