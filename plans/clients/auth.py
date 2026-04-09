from __future__ import annotations

from typing import Optional

import requests


class AuthServiceClient:
    """Проверка существования пользователя в auth-service."""

    def __init__(self, base_url: str, timeout: float = 10.0, session: Optional[requests.Session] = None):
        """base_url — корень auth-service; session опционально для тестов."""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = session or requests.Session()

    def user_exists(self, user_id: int) -> bool:
        """GET /users/{id}/: False при 404, иначе raise_for_status и True."""
        url = f'{self.base_url}/users/{user_id}/'
        response = self.session.get(url, timeout=self.timeout)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True
