"""Masquage des données personnelles (e-mails, téléphones, noms de personnes physiques).

Approche : regex (e-mails, téléphones, civilité + nom) et liste de noms propres au dossier
(champs de contact structurés de l'avis). Pas exhaustif : un nom sans civilité dans un texte
libre et absent des champs de contact n'est pas détecté (limite documentée).
"""

import re
from collections.abc import Iterable
from typing import Any

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_FR = r"(?:(?:\+|00)\s?33[\s.]?(?:\(0\)[\s.]?)?|0)[1-9](?:[\s.-]?\d{2}){4}"
_PHONE_INTL = r"\+\d{1,3}[\s.]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,4}){2,4}"
PHONE_RE = re.compile(rf"(?<![\w+]){_PHONE_FR}(?!\d)|(?<![\w+]){_PHONE_INTL}(?!\d)")
_CAP = r"[A-ZÀ-ÖØ-Þ][\w'’-]+"
CIVILITY_RE = re.compile(
    rf"\b(?:M\.|MM\.|Mme|Mlle|Monsieur|Madame|Mademoiselle|Mr|Mrs)\s+(?!(?:le|la|les|l')\b)"
    rf"{_CAP}(?:\s+{_CAP}){{0,2}}"
)
# Mots administratifs qu'on ne traite jamais comme un nom de personne (liste noire de contact).
_SERVICE_WORDS = {
    "service", "services", "mairie", "commune", "ville", "direction", "marchés", "marches",
    "publics", "public", "commande", "commandes", "achats", "achat", "secrétariat", "secretariat",
    "département", "departement", "communauté", "communaute", "cabinet", "bureau", "pôle",
    "pole", "juridique", "administratif", "affaires", "générales", "generales", "des", "de",
    "du", "la", "le", "les", "et", "en", "au", "aux", "pour", "sur", "maire", "adjoint",
    "président", "presidente", "directeur", "directrice", "responsable", "chargé", "chargée",
    "agent", "contact", "accueil", "madame", "monsieur", "mme", "mlle",
}  # fmt: skip


# Si l'un de ces mots figure dans le champ de contact, c'est un service ou une organisation.
_ORG_WORDS = {
    "mairie", "commune", "ville", "service", "services", "département", "departement",
    "communauté", "communaute", "syndicat", "direction", "centre", "hôtel", "hotel", "pôle",
    "pole", "cabinet", "bureau", "secrétariat", "secretariat", "métropole", "metropole",
    "agglomération", "agglomeration", "région", "region", "établissement", "etablissement",
    "office", "société", "societe", "association", "université", "universite", "ccas", "sdis",
}  # fmt: skip


_PARTICLES = {"van", "von", "dit", "ben", "del", "della", "dos", "das", "bin", "ter", "ten"}


def _words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[\w'’-]{3,}", text)}


def _name_tokens(raw: str) -> list[str]:
    """Jetons de nom à masquer extraits d'un champ de contact (avant la première virgule)."""
    head = re.split(r"[,;(]", raw, maxsplit=1)[0].strip()
    if _words(head) & _ORG_WORDS:
        return []
    raw_toks = [t for t in re.split(r"[\s/]+", head) if t]
    # Un nom de personne : 1 à 4 mots, tous en majuscule initiale (hors particules) ; sinon c'est
    # un libellé (« Cellule juridique des contrats ... ») et rien n'est masqué.
    if len(raw_toks) > 4 or any(
        len(t) >= 3 and t[0].islower() and t.lower() not in _PARTICLES for t in raw_toks
    ):
        return []
    toks = [t for t in raw_toks if len(t) >= 3 and t.lower() not in _SERVICE_WORDS]
    # Si le champ ressemble à un libellé de service (aucun jeton ne reste ou tout est un mot
    # courant), rien n'est masqué ; sinon on masque chaque jeton.
    return toks


class Masker:
    def __init__(self, names: Iterable[str] = (), keep: Iterable[str] = ()):
        """`keep` : textes (nom de l'acheteur, ville) dont les mots ne sont jamais masqués."""
        kept = set().union(*(_words(k) for k in keep)) if keep else set()
        toks: list[str] = []
        for raw in names:
            if raw and raw.strip():
                toks.extend(_name_tokens(raw))
        toks = sorted(
            {
                t.strip(".,;:")
                for t in toks
                if t.strip(".,;:") and t.strip(".,;:").lower() not in kept
            },
            key=len,
            reverse=True,
        )
        self._name_re = (
            re.compile(
                r"(?<![\w-])(?:" + "|".join(re.escape(t) for t in toks) + r")(?![\w-])",
                re.IGNORECASE,
            )
            if toks
            else None
        )

    def mask(self, text: str) -> str:
        text = EMAIL_RE.sub("[EMAIL]", text)
        text = PHONE_RE.sub("[TEL]", text)
        text = CIVILITY_RE.sub("[PERSONNE]", text)
        if self._name_re:
            text = self._name_re.sub("[PERSONNE]", text)
        return re.sub(r"\[PERSONNE\](?:\s+\[PERSONNE\])+", "[PERSONNE]", text)

    def mask_obj(self, obj: Any) -> Any:
        if isinstance(obj, str):
            return self.mask(obj)
        if isinstance(obj, list):
            return [self.mask_obj(x) for x in obj]
        if isinstance(obj, dict):
            return {k: self.mask_obj(v) for k, v in obj.items()}
        return obj


def find_residual_pii(text: str) -> list[str]:
    """Fuites détectables par regex (e-mail, téléphone) : contrôle final du jeu."""
    return EMAIL_RE.findall(text) + PHONE_RE.findall(text)
