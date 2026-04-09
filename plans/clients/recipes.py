from __future__ import annotations

from typing import Any, Optional
import requests


class RecipesServiceClient:
    """HTTP-клиент к recipes-service: загрузка списка рецептов с учётом пагинации DRF."""

    def __init__(self, base_url: str, timeout: float = 10.0, session: Optional[requests.Session] = None):
        """base_url — корень сервиса; session опционально подставляется для тестов."""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = session or requests.Session()

    def list_recipes(self) -> list[dict[str, Any]]:
        """GET /recipes/ и все страницы по полю next; поддерживает ответ-список или {results, next}."""
        url = f'{self.base_url}/recipes/'
        collected: list[dict[str, Any]] = []
        while url:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                collected.extend(data)
                break
            batch = data.get('results')
            if batch is None:
                break
            collected.extend(batch)
            url = data.get('next')
        return collected
