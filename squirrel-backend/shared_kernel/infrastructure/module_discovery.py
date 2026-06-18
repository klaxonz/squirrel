"""Module discovery utilities for finding classes in packages."""

import importlib
import pkgutil


def import_classes_from_package(
    package: str,
    base_class: type | None = None,
    recursive: bool = False,
) -> list[type]:
    """Import all classes from a package that optionally inherit from a base class.

    Args:
        package: Package name to search
        base_class: Optional base class to filter by
        recursive: Whether to search recursively in subpackages

    Returns:
        List of discovered classes

    """
    discovered_classes = []

    try:
        package_module = importlib.import_module(package)
    except ImportError:
        return discovered_classes

    # Get classes from the package module itself
    for name in dir(package_module):
        obj = getattr(package_module, name)
        if isinstance(obj, type) and (base_class is None or issubclass(obj, base_class)):
            discovered_classes.append(obj)

    if not recursive:
        return discovered_classes

    # Search subpackages
    package_path = getattr(package_module, '__path__', None)
    if package_path is None:
        return discovered_classes

    for _importer, modname, _ispkg in pkgutil.walk_packages(package_path):
        full_module_name = f"{package}.{modname}"

        try:
            module = importlib.import_module(full_module_name)
        except ImportError:
            continue

        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and (base_class is None or issubclass(obj, base_class)):
                discovered_classes.append(obj)

    return discovered_classes
