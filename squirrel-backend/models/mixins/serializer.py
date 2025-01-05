from datetime import datetime
from decimal import Decimal
from typing import Any, Set, Dict, Optional, Type, TypeVar
from sqlalchemy.orm import class_mapper

T = TypeVar('T', bound='SerializerMixin')


class SerializerMixin:
    """Mixin for SQLAlchemy model serialization and deserialization"""

    def to_dict(
            self,
            exclude: Set[str] = None,
            include: Set[str] = None,
            nested: bool = False,
            nested_depth: int = 1
    ) -> Dict[str, Any]:
        """
        Convert SQLAlchemy model instance to dictionary
        
        Args:
            exclude: Fields to exclude
            include: Fields to include (if set, only these fields will be included)
            nested: Whether to include relationships
            nested_depth: How deep to follow relationships
        """
        data = {}
        exclude = exclude or set()

        # Get all columns
        mapper = class_mapper(self.__class__)
        for column in mapper.columns:
            if column.key in exclude:
                continue
            if include and column.key not in include:
                continue
            data[column.key] = self._serialize_value(getattr(self, column.key))

        # Handle relationships if requested
        if nested and nested_depth > 0:
            for relation in mapper.relationships:
                if relation.key in exclude:
                    continue
                if include and relation.key not in include:
                    continue

                value = getattr(self, relation.key)
                if value is None:
                    data[relation.key] = None
                elif isinstance(value, list):
                    data[relation.key] = [
                        item.to_dict(
                            nested=True,
                            nested_depth=nested_depth - 1
                        ) if hasattr(item, 'to_dict') else item
                        for item in value
                    ]
                else:
                    data[relation.key] = value.to_dict(
                        nested=True,
                        nested_depth=nested_depth - 1
                    ) if hasattr(value, 'to_dict') else value

        return data

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value"""
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return str(value)
        elif isinstance(value, bytes):
            return value.decode('utf-8')
        return value

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create model instance from dictionary
        
        Args:
            data: Dictionary containing model data
            
        Returns:
            Model instance
        """
        # Filter out invalid fields
        mapper = class_mapper(cls)
        model_data = {}

        # Handle simple columns
        for key, value in data.items():
            if key in mapper.columns.keys():
                model_data[key] = cls._deserialize_value(
                    value,
                    mapper.columns[key].type.python_type
                )

        # Create instance
        return cls(**model_data)

    @staticmethod
    def _deserialize_value(value: Any, target_type: Type) -> Any:
        """Convert value to appropriate Python type"""
        if value is None:
            return None

        try:
            if target_type == datetime:
                if isinstance(value, str):
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            return target_type(value)
        except (ValueError, TypeError):
            return None
