from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet

from core.config import settings

logger = logging.getLogger(__name__)


class RssCredentialService:
    def _fernet(self) -> Fernet:
        digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def encrypt_credential(self, value: str) -> str:
        return self._fernet().encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_credential(self, value: str) -> str:
        return self._fernet().decrypt(value.encode("utf-8")).decode("utf-8")


_default = RssCredentialService()
encrypt_credential = _default.encrypt_credential
decrypt_credential = _default.decrypt_credential
