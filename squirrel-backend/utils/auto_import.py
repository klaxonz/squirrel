import importlib
import logging
from pathlib import Path
from typing import List, Type, Union

logger = logging.getLogger()


class ModuleImporter:
    """General module auto importer"""

    @staticmethod
    def import_classes(
            directory: Union[str, Path],
            base_class: Type = None,
            recursive: bool = False,
            exclude_files: List[str] = None,
            exclude_classes: List[str] = None
    ) -> List[Type]:
        """
        Import all classes in the specified directory, optionally filtering by base class
        
        Args:
            directory: Directory path to scan
            base_class: Optional base class to filter by
            recursive: Whether to scan subdirectories
            exclude_files: List of file names to exclude
            exclude_classes: List of class names to exclude
            
        Returns:
            List of imported classes
            
        Examples:
            >>> from fastapi import APIRouter
            >>> routers = ModuleImporter.import_classes("routers", APIRouter)
        """
        classes = []
        directory = Path(directory).resolve()
        exclude_files = exclude_files or ["__init__.py"]
        exclude_classes = exclude_classes or []

        if not directory.exists():
            logger.warning(f"Directory {directory} does not exist")
            return classes

        # Get all .py files
        pattern = "**/*.py" if recursive else "*.py"
        for file in directory.glob(pattern):
            if file.name in exclude_files:
                continue

            try:
                # Convert path to module path
                # e.g., 'models/user/account.py' -> 'models.user.account'
                relative_path = file.relative_to(directory)
                module_parts = list(relative_path.parent.parts)
                
                if module_parts and module_parts[0] == '.':
                    module_parts.pop(0)
                    
                if module_parts:
                    module_path = f"{directory.name}.{'.'.join(module_parts)}.{file.stem}"
                else:
                    module_path = f"{directory.name}.{file.stem}"

                # Import module
                module = importlib.import_module(module_path)
                
                # Get all classes
                for attr_name in dir(module):
                    if attr_name in exclude_classes:
                        continue
                        
                    attr = getattr(module, attr_name)
                    if not isinstance(attr, type):
                        continue
                        
                    # If base_class is specified, filter by it
                    if base_class is not None:
                        if issubclass(attr, base_class) and attr != base_class:
                            classes.append(attr)
                    else:
                        # Import all classes if no base_class specified
                        classes.append(attr)
                        
            except ImportError as e:
                logger.error(f"Failed to import {file}: {e}")
                continue
            except ValueError as e:
                logger.error(f"Failed to process {file}: {e}")
                continue
            
        return classes


