"""Client minimal de l'API Explore v2.1 du jeu BOAMP (DILA, Opendatasoft), avec cache disque."""

import gzip
import hashlib
import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path

BASE_URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"


def _http_get(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("HTTPS requis")
    req = urllib.request.Request(  # noqa: S310 - schéma vérifié ci-dessus
        url, headers={"Accept-Encoding": "gzip", "User-Agent": "boamp-llm-eval"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        body = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body


class BoampClient:
    def __init__(
        self,
        cache_dir: Path | str = "data/raw",
        transport: Callable[[str], bytes] = _http_get,
        base_url: str = BASE_URL,
    ):
        self.cache_dir = Path(cache_dir)
        self.transport = transport
        self.base_url = base_url

    def url(self, **params: object) -> str:
        clean = {k: v for k, v in params.items() if v is not None}
        return f"{self.base_url}?{urllib.parse.urlencode(sorted(clean.items()))}"

    def records(
        self,
        where: str | None = None,
        select: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str | None = None,
    ) -> dict:
        url = self.url(where=where, select=select, limit=limit, offset=offset, order_by=order_by)
        path = self.cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        body = self.transport(url)
        data = json.loads(body)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
