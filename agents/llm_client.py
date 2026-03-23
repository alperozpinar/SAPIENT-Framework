"""
Unified LLM Client — Anthropic ve OpenAI backend'lerini tek arayüzde birleştirir.
Hem sync (chat) hem async (achat) destekler.
Retry with exponential backoff for transient errors (500, 529, rate-limit).
"""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Optional

import anthropic
import openai


PROVIDER_MAP = {
    "claude-sonnet-4-20250514": "anthropic",
    "gpt-4o": "openai",
    "gpt-4o-2024-11-20": "openai",
    "gpt-4o-mini": "openai",
}

PRICING = {  # (input_per_M_tokens, output_per_M_tokens)
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "gpt-4o":                   (2.50, 10.00),
    "gpt-4o-2024-11-20":        (2.50, 10.00),
    "gpt-4o-mini":              (0.15,  0.60),
}

MAX_RETRIES = 5
BASE_DELAY = 2.0  # seconds


def get_provider(model: str) -> str:
    """Model adından provider döndür."""
    provider = PROVIDER_MAP.get(model)
    if not provider:
        raise ValueError(
            f"Bilinmeyen model: {model}. "
            f"Desteklenen modeller: {list(PROVIDER_MAP.keys())}"
        )
    return provider


def _is_retryable(exc: Exception) -> bool:
    """Transient (yeniden denenebilir) hata mı?"""
    if isinstance(exc, anthropic.InternalServerError):  # 500
        return True
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code in (429, 500, 502, 503, 529):
        return True
    if isinstance(exc, anthropic.APIConnectionError):
        return True
    if isinstance(exc, openai.APIStatusError) and exc.status_code in (429, 500, 502, 503):
        return True
    if isinstance(exc, openai.APIConnectionError):
        return True
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    return False


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter."""
    delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
    return min(delay, 60.0)  # cap at 60s


@dataclass
class LLMResponse:
    """Tüm LLM çağrılarının standart dönüş tipi."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: float

    @property
    def cost_usd(self) -> float:
        pricing = PRICING.get(self.model, (0, 0))
        return (
            (self.input_tokens / 1_000_000) * pricing[0]
            + (self.output_tokens / 1_000_000) * pricing[1]
        )


def chat(
    system_prompt: str,
    user_message: str,
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: str,
    messages: Optional[list[dict]] = None,
) -> LLMResponse:
    """
    Sync LLM çağrısı.

    messages verilirse multi-turn olarak kullanılır (followup için).
    Verilmezse user_message'dan tek-turn messages oluşturulur.
    Retry with exponential backoff for transient errors.
    """
    provider = get_provider(model)
    last_exc = None

    for attempt in range(MAX_RETRIES):
        try:
            start = time.perf_counter()

            if provider == "anthropic":
                client = anthropic.Anthropic(api_key=api_key)
                msgs = messages if messages is not None else [{"role": "user", "content": user_message}]
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=msgs,
                )
                content = response.content[0].text
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            elif provider == "openai":
                client = openai.OpenAI(api_key=api_key)
                oai_messages = [{"role": "system", "content": system_prompt}]
                if messages is None:
                    oai_messages.append({"role": "user", "content": user_message})
                else:
                    oai_messages.extend(messages)
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=oai_messages,
                )
                content = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            elapsed_ms = (time.perf_counter() - start) * 1000

            return LLMResponse(
                content=content,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round(elapsed_ms, 1),
            )

        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES - 1:
                raise
            delay = _backoff_delay(attempt)
            print(f"  [retry {attempt+1}/{MAX_RETRIES}] {type(exc).__name__}: {exc} -- waiting {delay:.1f}s")
            time.sleep(delay)

    raise last_exc  # should not reach here


async def achat(
    system_prompt: str,
    user_message: str,
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: str,
    messages: Optional[list[dict]] = None,
) -> LLMResponse:
    """
    Async LLM çağrısı (parallel_runner için).

    messages verilirse multi-turn olarak kullanılır (followup için).
    Verilmezse user_message'dan tek-turn messages oluşturulur.
    Retry with exponential backoff for transient errors.
    """
    provider = get_provider(model)
    last_exc = None

    for attempt in range(MAX_RETRIES):
        try:
            start = time.perf_counter()

            if provider == "anthropic":
                client = anthropic.AsyncAnthropic(api_key=api_key)
                msgs = messages if messages is not None else [{"role": "user", "content": user_message}]
                response = await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=msgs,
                )
                content = response.content[0].text
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            elif provider == "openai":
                client = openai.AsyncOpenAI(api_key=api_key)
                oai_messages = [{"role": "system", "content": system_prompt}]
                if messages is None:
                    oai_messages.append({"role": "user", "content": user_message})
                else:
                    oai_messages.extend(messages)
                response = await client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=oai_messages,
                )
                content = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            elapsed_ms = (time.perf_counter() - start) * 1000

            return LLMResponse(
                content=content,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round(elapsed_ms, 1),
            )

        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES - 1:
                raise
            delay = _backoff_delay(attempt)
            print(f"  [retry {attempt+1}/{MAX_RETRIES}] {type(exc).__name__}: {exc} -- waiting {delay:.1f}s")
            await asyncio.sleep(delay)

    raise last_exc  # should not reach here
