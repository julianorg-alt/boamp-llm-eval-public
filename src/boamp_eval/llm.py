"""Clients : HTTP réel (stdlib, sans dépendance) et rejeu de réponses enregistrées."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://api.anthropic.com"
API_VERSION = "2026-10-21"  # en-tête anthropic-version des exemples de la doc (docs/sources.md)


class HttpClient:
    """Appel réel. La clé vient de l'environnement (ANTHROPIC_API_KEY), jamais écrite ni affichée."""

    live = True

    def __init__(self, *, retries: int = 3, timeout: float = 300) -> None:
        self._key = os.environ["ANTHROPIC_API_KEY"]
        self.retries, self.timeout = retries, timeout

    def _call(self, method: str, path: str, body: dict | None = None) -> bytes:
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(  # noqa: S310
                BASE_URL + path,
                data=data,
                method=method,
                headers={
                    "content-type": "application/json",
                    "x-api-key": self._key,
                    "anthropic-version": API_VERSION,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
                    return r.read()
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                if e.code in (429, 500, 502, 503, 529) and attempt < self.retries:
                    time.sleep(2**attempt * 2)
                    continue
                raise RuntimeError(f"HTTP {e.code}: {detail}") from None
        raise RuntimeError("inatteignable")

    def create(self, params: dict, *, key: str) -> dict:  # noqa: ARG002
        return json.loads(self._call("POST", "/v1/messages", params))

    def create_batch(self, requests: list[dict]) -> dict:
        return json.loads(self._call("POST", "/v1/messages/batches", {"requests": requests}))

    def get_batch(self, batch_id: str) -> dict:
        return json.loads(self._call("GET", f"/v1/messages/batches/{batch_id}"))

    def batch_results(self, batch_id: str) -> list[str]:
        raw = self._call("GET", f"/v1/messages/batches/{batch_id}/results")
        return [ln for ln in raw.decode().splitlines() if ln.strip()]

    def count_tokens(self, params: dict) -> int:
        """Comptage gratuit (docs/sources.md) ; seuls les champs acceptés sont envoyés."""
        keep = {
            k: params[k] for k in ("model", "system", "messages", "output_config") if k in params
        }
        return json.loads(self._call("POST", "/v1/messages/count_tokens", keep))["input_tokens"]


class RecordedClient:
    """Rejoue des réponses enregistrées par `harness.run` (JSONL {idweb, model, response})."""

    live = False

    def __init__(self, path: Path) -> None:
        self.by_key = {}
        for line in Path(path).read_text().splitlines():
            d = json.loads(line)
            self.by_key[d["idweb"]] = d["response"]

    def create(self, params: dict, *, key: str) -> dict:  # noqa: ARG002
        return self.by_key[key]
