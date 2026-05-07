from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class MistralAPIError(Exception):
    """Ошибка ответа Mistral API или сети."""


class MistralClient:
    """Клиент Chat Completions Mistral (OpenAI-совместимый эндпоинт)."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = 'https://api.mistral.ai/v1',
        model: str = 'mistral-small-latest',
        timeout: float = 120.0,
        session: requests.Session | None = None,
    ):
        if not api_key or not str(api_key).strip():
            raise ValueError('Mistral API key is required')
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self._session = session or requests.Session()

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.6,
        max_tokens: int | None = 2048,
    ) -> str:
        url = f'{self.base_url}/chat/completions'
        body: dict[str, Any] = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
        }
        if max_tokens is not None:
            body['max_tokens'] = max_tokens

        try:
            response = self._session.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.exception('Mistral request failed')
            raise MistralAPIError(str(exc)) from exc

        if response.status_code >= 400:
            raise MistralAPIError(
                f'HTTP {response.status_code}: {response.text[:500]}',
            )

        data = response.json()
        choices = data.get('choices') or []
        if not choices:
            raise MistralAPIError('Empty choices in Mistral response')

        message = choices[0].get('message') or {}
        content = message.get('content')
        if content is None:
            raise MistralAPIError('No content in Mistral response')

        return str(content).strip()

    @staticmethod
    def parse_json_suggestions(raw: str) -> dict[str, Any]:
        """Достаёт JSON из ответа модели; при неудаче оборачивает текст в структуру."""
        text = raw.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                logger.warning('Could not parse JSON from Mistral output, using raw text')

        return {
            'summary': text[:8000],
            'parse_error': True,
        }
