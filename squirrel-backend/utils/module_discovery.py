from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from types import ModuleType
from typing import List, Sequence, Type, Union

logger = logging.getLogger()


def import_classes_from_package(
    package: Union[str, ModuleType],
    base_class: Type | None = None,
    recursive: bool = True,
    exclude_modules: Sequence[str] | None = None,
    exclude_classes: Sequence[str] | None = None,
    include_private_modules: bool = False,
    defined_in_module_only: bool = True,
) -> List[Type]:
    """
    Discover and import classes from a package using pkgutil + importlib + inspect.

    Args:
        package: Package object or package name (string).
        base_class: If provided, only subclasses of this base (excluding the base itself) are returned.
        recursive: Whether to walk subpackages recursively. If False, only direct children are scanned.
        exclude_modules: Module names to exclude. Supports either full dotted names (e.g. 'pkg.mod')
                         or basenames (e.g. 'mod').
        exclude_classes: Class names to exclude.
        include_private_modules: If False, modules whose basename starts with '_' are skipped.
        defined_in_module_only: If True, only classes defined in the module itself are returned
                                (i.e., cls.__module__ == module.__name__).

    Returns:
        A list of discovered class objects.

    """
    exclude_modules = list(exclude_modules or [])
    exclude_classes = set(exclude_classes or [])

    # Resolve package module
    try:
        pkg_mod = importlib.import_module(package) if isinstance(package, str) else package
    except ImportError as e:
        logger.error("Failed to import package '%s': %s", package, e)
        return []

    results: list[Type] = []

    def should_exclude_module(candidate_name: str) -> bool:
        base = candidate_name.rsplit('.', 1)[-1]
        if not include_private_modules and base.startswith('_'):
            return True
        # Allow excluding by full dotted name or by basename
        return candidate_name in exclude_modules or base in exclude_modules

    def scan_module(full_module_name: str):
        try:
            module = importlib.import_module(full_module_name)
        except ImportError as e:
            logger.warning("Failed to import module '%s' (skipped): %s", full_module_name, e)
            return

        for _, cls in inspect.getmembers(module, inspect.isclass):
            # Optionally only keep classes defined in this module
            if defined_in_module_only and getattr(cls, '__module__', None) != module.__name__:
                continue
            if cls.__name__ in exclude_classes:
                continue
            if base_class is not None:
                try:
                    if issubclass(cls, base_class) and cls is not base_class:
                        results.append(cls)
                except TypeError:
                    # Some edge cases may raise TypeError with issubclass
                    continue
            else:
                results.append(cls)

    # If it's a simple module (not a package), just scan it directly
    if not hasattr(pkg_mod, '__path__'):
        scan_module(pkg_mod.__name__)
        return results

    # For a package, scan the package itself first
    scan_module(pkg_mod.__name__)

    # Iterate child modules/packages
    iter_func = pkgutil.walk_packages if recursive else pkgutil.iter_modules
    # Both functions accept (path, prefix). walk_packages yields (finder, name, ispkg)
    for _, child_module_name, _ in iter_func(pkg_mod.__path__, pkg_mod.__name__ + "."):
        if should_exclude_module(child_module_name):
            continue
        scan_module(child_module_name)

    return results

