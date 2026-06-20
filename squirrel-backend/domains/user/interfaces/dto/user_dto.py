"""DTOs for the user domain HTTP boundary.

These decouple the HTTP/auth layer from the SQLAlchemy ORM ``User`` model so
that authentication dependencies hand routes a typed, serialisation-safe
object rather than a raw ORM instance.
"""

from pydantic import BaseModel, ConfigDict


class CurrentUserDto(BaseModel):
    """The authenticated user, as seen by request handlers.

    Only carries the fields a route actually needs from the resolved identity.
    Intentionally *excludes* sensitive columns such as ``token_version`` and
    any ORM relationships -- those must be fetched explicitly when required.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
