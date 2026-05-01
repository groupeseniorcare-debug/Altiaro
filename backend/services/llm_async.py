"""
Async LLM wrapper — Phase 4.b.

Problème : `emergentintegrations.llm.chat.LlmChat.send_message()` est déclaré
`async def` mais appelle en interne `litellm.completion(...)` qui est SYNCHRONE
(la lib litellm fait l'HTTP request en bloquant). Conséquence : pendant un
appel Claude/Nano-Banana de 10-90 s, l'event loop uvicorn est bloqué et toutes
les autres requêtes (`/api/health`, `/launch-status`, etc.) attendent.

Solution : exécuter `chat.send_message(...)` dans un thread séparé via
`asyncio.to_thread(...)`. Le thread bloque, mais l'event loop reste libre.

⚠️ ATTENTION — `chat.send_message(...)` est ELLE-MÊME une coroutine. On ne
peut pas la passer directement à `to_thread` (qui attend un callable sync).
On doit envelopper :
    asyncio.to_thread(asyncio.run, chat.send_message(...))
        # crée un nouveau loop dans le thread, exécute la coroutine,
        # le ferme. Pas idéal mais propre.

Alternative testée : `asyncio.get_event_loop().run_in_executor(None, ...)` —
même résultat mais plus verbeux.

Compatibilité : ce wrapper REMPLACE l'appel `await chat.send_message(msg)` par
`await run_chat_in_thread(chat, msg)`. Tout le reste (circuit-breaker, retry,
cost tracker) reste intact car branché en amont dans `safe_llm_call`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("altiaro.llm_async")


async def _run_coro_in_new_loop(coro_factory):
    """Run a coroutine produced by `coro_factory()` inside a fresh event loop
    in a thread. Returns the coroutine result.

    `coro_factory` must be a zero-arg callable that returns a coroutine,
    NOT the coroutine itself (a coroutine can only be awaited once and from
    the loop that created it).
    """
    def _runner():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro_factory())
        finally:
            try:
                loop.close()
            except Exception:
                pass
            asyncio.set_event_loop(None)

    return await asyncio.to_thread(_runner)


async def send_message_threaded(chat, user_message) -> Any:
    """Equivalent à `await chat.send_message(user_message)` mais sans bloquer
    l'event loop principal pendant la requête HTTP litellm.
    """
    return await _run_coro_in_new_loop(lambda: chat.send_message(user_message))


async def send_multimodal_threaded(chat, user_message) -> Any:
    """Idem pour `send_message_multimodal_response` (Nano Banana)."""
    return await _run_coro_in_new_loop(
        lambda: chat.send_message_multimodal_response(user_message)
    )
