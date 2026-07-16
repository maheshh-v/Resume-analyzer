"""Provider-agnostic structured-output LLM providers.

Every provider implements the same contract: give it a system+user prompt and a pydantic
schema, get back a validated instance of that schema plus token usage. Swapping providers
is a one-line env change (`LLM_PROVIDER=gemini|openai|fake`) — nothing in `pipeline/` ever
imports an SDK directly.

Real providers require API keys and are exercised by manual/live testing only; the
automated test suite runs entirely against FakeProvider so it's deterministic and free.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class StructuredResult(Generic[T]):
    data: T
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate_structured(self, *, system: str, user: str, schema: type[T]) -> StructuredResult[T]: ...


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def generate_structured(self, *, system: str, user: str, schema: type[T]) -> StructuredResult[T]:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)
        response = await client.aio.models.generate_content(
            model=self._model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
        parsed: T = response.parsed if response.parsed is not None else schema.model_validate_json(response.text)
        usage = getattr(response, "usage_metadata", None)
        return StructuredResult(
            data=parsed,
            model=self._model,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def generate_structured(self, *, system: str, user: str, schema: type[T]) -> StructuredResult[T]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)
        completion = await client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=schema,
            temperature=0.2,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI returned no parsed structured output")
        usage = completion.usage
        return StructuredResult(
            data=parsed,
            model=self._model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )


@dataclass
class FakeProvider(LLMProvider):
    """Deterministic provider for tests. Queue canned responses (schema instances or dicts);
    each call pops the next one. Raises if the queue runs dry so tests fail loudly on
    unexpected extra calls rather than silently returning garbage."""

    name: str = "fake"
    responses: list[BaseModel | dict] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)

    async def generate_structured(self, *, system: str, user: str, schema: type[T]) -> StructuredResult[T]:
        self.calls.append({"system": system, "user": user, "schema": schema})
        if not self.responses:
            raise AssertionError("FakeProvider: no canned response queued for this call")
        next_response = self.responses.pop(0)
        if isinstance(next_response, BaseModel):
            data = schema.model_validate(next_response.model_dump())
        else:
            data = schema.model_validate(next_response)
        return StructuredResult(data=data, model="fake-model", input_tokens=0, output_tokens=0)


def dump_schema_example(instance: BaseModel) -> str:
    return json.dumps(instance.model_dump(), indent=2)
