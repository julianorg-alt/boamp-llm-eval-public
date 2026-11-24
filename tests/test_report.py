"""Bootstrap apparié : même tirage d'avis pour A et B (aucun appel réseau)."""

import pytest

from boamp_eval import report


def _rows(values):
    return [{"idweb": f"id{i:03d}", "v": v} for i, v in enumerate(values)]


def _mean(rows):
    return sum(r["v"] for r in rows) / len(rows)


def test_diff_constante_ic_degenere():
    a = _rows([0.9] * 40)
    b = _rows([0.8] * 40)
    d, lo, hi = report.paired_diff_ci(a, b, _mean, n_boot=300)
    assert d == pytest.approx(0.1) and lo == pytest.approx(0.1) and hi == pytest.approx(0.1)
    assert report.excludes_zero((d, lo, hi))


def test_pairing_ic_plus_etroit_que_non_apparie():
    # A = B + 0,1 avis par avis, mais forte variance entre avis : l'appariement l'annule.
    base = [(i % 10) / 10 for i in range(60)]
    a, b = _rows([x + 0.1 for x in base]), _rows(base)
    d, lo, hi = report.paired_diff_ci(a, b, _mean, n_boot=500)
    assert hi - lo < 1e-9 and d == pytest.approx(0.1)


def test_zero_inclus_quand_pas_d_ecart():
    vals = [1.0, 0.0] * 30
    a, b = _rows(vals), _rows(vals[::-1])  # moyennes égales, écarts de signes opposés
    d, lo, hi = report.paired_diff_ci(a, b, _mean, n_boot=500)
    assert d == pytest.approx(0.0) and lo < 0 < hi
    assert not report.excludes_zero((d, lo, hi))


def test_reproductible_et_ordre_indifferent():
    a, b = _rows([0.1, 0.5, 0.9, 0.3, 0.7]), _rows([0.2, 0.4, 0.8, 0.1, 0.9])
    r1 = report.paired_diff_ci(a, b, _mean, n_boot=200, seed=7)
    r2 = report.paired_diff_ci(a[::-1], b, _mean, n_boot=200, seed=7)
    assert r1 == r2


def test_ensembles_d_avis_differents_refuses():
    with pytest.raises(ValueError):
        report.paired_diff_ci(_rows([1, 0]), _rows([1, 0, 1]), _mean)


def test_alpha_plus_petit_donne_ic_plus_large():
    a, b = _rows([0.9, 0.1, 0.8, 0.4, 0.6, 0.2] * 5), _rows([0.7, 0.2, 0.9, 0.1, 0.5, 0.3] * 5)
    _, lo95, hi95 = report.paired_diff_ci(a, b, _mean, n_boot=1000, alpha=0.05)
    _, lo98, hi98 = report.paired_diff_ci(a, b, _mean, n_boot=1000, alpha=0.05 / 3)
    assert lo98 <= lo95 and hi98 >= hi95
