from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3


class MistralAPIError(Exception):
    """Ошибка ответа Mistral API или сети."""


class MistralClient:
    """Клиент Chat Completions Mistral (OpenAI-совместимый эндпоинт), через httpx."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = 'https://api.mistral.ai/v1',
        model: str = 'mistral-small-latest',
        timeout: float = 120.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        proxy: str | None = None,
    ):
        if not api_key or not str(api_key).strip():
            raise ValueError('Mistral API key is required')
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.read_timeout = max(float(timeout), 30.0)
        self.max_retries = max(1, int(max_retries))
        self.proxy = proxy

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.6,
        max_tokens: int | None = 1024,
    ) -> str:
        url = f'{self.base_url}/chat/completions'
        body: dict[str, Any] = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
        }
        if max_tokens is not None:
            body['max_tokens'] = max_tokens

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Foodgram-MealPlanner/1.0',
        }

        timeout = httpx.Timeout(
            connect=45.0,
            read=self.read_timeout,
            write=120.0,
            pool=10.0,
        )
        limits = httpx.Limits(max_keepalive_connections=0, max_connections=2)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(
                    timeout=timeout,
                    limits=limits,
                    proxy=self.proxy,
                    http2=False,
                ) as client:
                    response = client.post(url, headers=headers, json=body)
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    'Mistral httpx сеть/обрыв (попытка %s/%s): %s',
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2.0 * (attempt + 1))
                continue

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

        assert last_exc is not None
        logger.exception('Mistral: исчерпаны повторы после обрыва соединения')
        raise MistralAPIError(str(last_exc)) from last_exc

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
