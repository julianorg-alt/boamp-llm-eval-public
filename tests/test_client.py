import json

from boamp_eval.client import BoampClient

PAGE = {"total_count": 3, "results": [{"idweb": "26-1"}, {"idweb": "26-2"}]}


def make(calls):
    def transport(url):
        calls.append(url)
        return json.dumps(PAGE).encode()

    return transport


def test_query_builds_url_and_caches(tmp_path):
    calls = []
    c = BoampClient(cache_dir=tmp_path, transport=make(calls))
    a = c.records(where="famille='MAPA'", select="idweb", limit=2, offset=0)
    b = c.records(where="famille='MAPA'", select="idweb", limit=2, offset=0)
    assert a == b == PAGE
    assert len(calls) == 1  # second call served from disk cache
    assert "where=famille%3D%27MAPA%27" in calls[0]
    assert "limit=2" in calls[0]


def test_cache_survives_new_client(tmp_path):
    calls = []
    BoampClient(cache_dir=tmp_path, transport=make(calls)).records(where="x=1", limit=1)
    BoampClient(cache_dir=tmp_path, transport=make(calls)).records(where="x=1", limit=1)
    assert len(calls) == 1


def test_different_params_different_cache(tmp_path):
    calls = []
    c = BoampClient(cache_dir=tmp_path, transport=make(calls))
    c.records(where="x=1", limit=1)
    c.records(where="x=2", limit=1)
    assert len(calls) == 2
