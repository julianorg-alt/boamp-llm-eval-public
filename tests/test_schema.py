"""Prompt, schéma de sortie, requêtes, analyse des réponses (hors réseau)."""

import json
import re

import pytest

from boamp_eval import schema as s
from boamp_eval.costs import Usage


def _msg(obj, stop="end_turn", **usage):
    u = {"input_tokens": 10, "output_tokens": 5, **usage}
    return {"stop_reason": stop, "usage": u, "content": [{"type": "text", "text": json.dumps(obj)}]}


FULL = {
    "acheteur": "Ville X", "objet": "Voirie", "lieu": "FRK26", "procedure": "open",
    "date_limite": "2026-11-04T12:00:00+01:00", "cpv": ["45233140"],
    "lots": [{"titre": "A"}], "montant_estime": {"valeur": 5.0, "devise": "EUR"},
    "criteres": [{"libelle": "Prix", "poids": 60}],
}  # fmt: skip


def test_params_forme_et_cache():
    p = s.build_params("claude-haiku-5-5", "texte de l'avis", effort="low", max_tokens=2000)
    assert p["model"] == "claude-haiku-5-5" and p["max_tokens"] == 2000
    assert p["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert p["system"][0]["text"] == s.SYSTEM_PROMPT
    assert p["messages"] == [{"role": "user", "content": "texte de l'avis"}]
    assert p["output_config"]["effort"] == "low"
    fmt = p["output_config"]["format"]
    assert fmt["type"] == "json_schema" and fmt["schema"] is s.OUTPUT_SCHEMA


def test_prompt_identique_pour_les_trois_modeles():
    ps = [
        s.build_params(m, "t") for m in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")
    ]
    assert len({json.dumps(p["system"]) for p in ps}) == 1
    assert len({json.dumps(p["output_config"]) for p in ps}) == 1


def test_schema_respecte_les_limites_de_l_api():
    sch = json.dumps(s.OUTPUT_SCHEMA)
    assert set(s.OUTPUT_SCHEMA["required"]) == set(s.OUTPUT_SCHEMA["properties"])  # 0 optionnel
    assert len(s.OUTPUT_SCHEMA["properties"]) == 9
    unions = sch.count('"anyOf"') + len(re.findall(r'"type": \[', sch))
    assert unions <= 16
    for bad in ("minimum", "maximum", "minLength", "maxLength", "oneOf", "$ref"):
        assert bad not in sch

    def objs(n):
        if isinstance(n, dict):
            if n.get("type") == "object":
                yield n
            for v in n.values():
                yield from objs(v)
        elif isinstance(n, list):
            for v in n:
                yield from objs(v)

    assert all(o["additionalProperties"] is False for o in objs(s.OUTPUT_SCHEMA))


def test_prompt_vocabulaire_et_injection():
    for w in ("adapted-open", "oth-single", "NUTS", "null", "ISO"):
        assert w in s.SYSTEM_PROMPT
    assert "instruction" in s.SYSTEM_PROMPT.lower()  # le texte de l'avis est une donnée


def test_parse_ok_et_usage():
    r = s.parse_response(_msg(FULL, cache_creation_input_tokens=7, cache_read_input_tokens=3))
    assert r.error is None and r.pred["acheteur"] == "Ville X"
    assert r.usage == Usage(10, 5, 7, 0, 3)  # 5 min par défaut si pas de détail


def test_parse_usage_detail_cache_1h():
    m = _msg(FULL, cache_creation_input_tokens=9)
    m["usage"]["cache_creation"] = {"ephemeral_5m_input_tokens": 4, "ephemeral_1h_input_tokens": 5}
    assert s.parse_response(m).usage == Usage(10, 5, 4, 5, 0)


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_parse_arrets_anormaux(stop):
    r = s.parse_response(_msg(FULL, stop=stop))
    assert r.pred is None and stop in r.error


def test_parse_json_invalide_et_forme_inattendue():
    m = _msg(FULL)
    m["content"][0]["text"] = "pas du json"
    assert s.parse_response(m).pred is None
    m["content"][0]["text"] = "[1, 2]"
    assert s.parse_response(m).error


def test_parse_ignore_les_blocs_de_reflexion():
    m = _msg(FULL)
    m["content"].insert(0, {"type": "thinking", "thinking": "..."})
    assert s.parse_response(m).pred["objet"] == "Voirie"


def test_parse_sanitise_les_vides():
    r = s.parse_response(_msg({**FULL, "lots": [], "montant_estime": None, "lieu": "  "}))
    assert r.pred["lots"] == [] and r.pred["montant_estime"] is None and r.pred["lieu"] is None


def test_requetes_batch_custom_id_valide():
    recs = [{"idweb": "26-123456", "texte": "a"}, {"idweb": "26-9", "texte": "b"}]
    reqs = s.batch_requests("claude-haiku-5-5", recs)
    assert [r["custom_id"] for r in reqs] == ["26-123456", "26-9"]
    assert all(re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", r["custom_id"]) for r in reqs)
    assert reqs[0]["params"]["messages"][0]["content"] == "a"


def test_ligne_de_resultat_batch():
    ok = {"custom_id": "x", "result": {"type": "succeeded", "message": _msg(FULL)}}
    cid, r = s.parse_batch_line(json.dumps(ok))
    assert cid == "x" and r.pred["objet"] == "Voirie"
    cid, r = s.parse_batch_line(
        json.dumps({"custom_id": "y", "result": {"type": "errored", "error": {}}})
    )
    assert cid == "y" and r.pred is None and "errored" in r.error
