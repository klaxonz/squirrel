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
            base_class: Type,
            recursive: bool = False,
            exclude_files: List[str] = None,
            exclude_classes: List[str] = None
    ) -> List[Type]:
        """
        Import all classes that inherit from base_class in the specified directory
        
        Args:
            directory: Directory path to scan
            base_class: Base class to filter by
            recursive: Whether to scan subdirectories
            exclude_files: List of file names to exclude
            exclude_classes: List of class names to exclude
            
        Returns:
            List of imported classes
            
        Examples:
            >>> from sqlmodel import SQLModel
            >>> models = ModuleImporter.import_classes("models", SQLModel)
            
            >>> from fastapi import APIRouter
            >>> routers = ModuleImporter.import_classes("routers", APIRouter)
        """
        classes = []
        directory = Path(directory)
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

            # Convert path to module path
            # e.g. models/user.py -> models.user
            module_path = f"{directory.name}.{file.stem}"

            try:
                # Import module
                module = importlib.import_module(module_path)
                
                # Get all classes that inherit from base_class
                for attr_name in dir(module):
                    if attr_name in exclude_classes:
                        continue
                        
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, base_class) and 
                        attr != base_class):
                        classes.append(attr)
                        
            except ImportError as e:
                logger.error(f"Failed to import {module_path}: {e}")
                continue
            
        return classes

    @classmethod
    def import_models(cls, directory: str = "models", **kwargs) -> List[Type]:
        """Helper method for importing SQLModel classes"""
        try:
            from sqlmodel import SQLModel
            return cls.import_classes(directory, SQLModel, **kwargs)
        except ImportError:
            logger.error("SQLModel not installed")
            return []

    @classmethod
    def import_routers(cls, directory: str = "routers", **kwargs) -> List[Type]:
        """Helper method for importing FastAPI routers"""
        try:
            from fastapi import APIRouter
            return cls.import_classes(directory, APIRouter, **kwargs)
        except ImportError:
            logger.error("FastAPI not installed")
            return []
