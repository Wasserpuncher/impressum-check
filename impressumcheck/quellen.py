"""Woher die Seiten kommen: eine URL, eine Datei, ein `dist/`-Ordner.

Der Ordner-Modus ist der wichtigere. Eine Prüfung, die erst nach dem Deploy
laufen kann, prüft eine Seite, die bereits online ist – das ist keine CI,
das ist eine Obduktion.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .parse import Seite, parse

USER_AGENT = "impressum-check (+https://github.com/Wasserpuncher/impressum-check)"

# Mehr als das braucht keine Impressumsprüfung. Wer 500 Seiten crawlt, um ein
# Impressum zu finden, hat das Problem nicht verstanden: es muss in zwei Klicks
# erreichbar sein, sonst ist es ohnehin ein Fund.
MAX_SEITEN = 400


@dataclass
class Sammlung:
    """Alle Seiten, die geprüft werden – plus die Startseite."""

    seiten: list[Seite]
    start: Seite | None
    #: Woher stammt das? Nur für die Ausgabe.
    herkunft: str = ""
    #: Wie viele Seiten es insgesamt gäbe. Weicht das von len(seiten) ab, wurde
    #: bei MAX_SEITEN abgeschnitten – und das muss dastehen. Ein Prüfer, der
    #: verschweigt, dass er nur einen Teil gesehen hat, ist ein Alibi.
    gesamt: int = 0

    def finde(self, *muster: str) -> Seite | None:
        """Erste Seite, deren Pfad – ersatzweise deren Titel – ein Muster trägt.

        Der Pfad hat Vorrang: /impressum/ ist eine Zusage, ein Titel ist nur
        ein Indiz. Aber der Titel muss mitgeprüft werden, sonst findet das
        Werkzeug ein Impressum nicht, auf das man es direkt gestoßen hat
        (`impressum-check impressum.html` – oder eine Datei, die anders heißt).
        """
        for feld in ("url", "titel"):
            for m in muster:
                for s in self.seiten:
                    if m in getattr(s, feld).lower():
                        return s
        return None


def _lies_html(pfad: Path) -> str:
    # errors="replace": eine kaputt kodierte Seite soll eine Meldung erzeugen,
    # keinen Stacktrace.
    return pfad.read_text(encoding="utf-8", errors="replace")


def aus_ordner(wurzel: Path) -> Sammlung:
    """Alle .html-Dateien unter `wurzel` – der CI-Fall."""
    alle = sorted(p for p in wurzel.rglob("*.html") if p.is_file())
    dateien = alle[:MAX_SEITEN]
    seiten = []
    start = None
    for p in dateien:
        rel = "/" + str(p.relative_to(wurzel)).replace("\\", "/")
        s = parse(_lies_html(p), url=rel)
        seiten.append(s)
        # Astro, Hugo, Jekyll & Co. legen /impressum/index.html an. Die
        # Startseite ist die index.html in der Wurzel.
        if rel == "/index.html":
            start = s
    return Sammlung(seiten=seiten, start=start, herkunft=str(wurzel), gesamt=len(alle))


def aus_datei(pfad: Path) -> Sammlung:
    s = parse(_lies_html(pfad), url="/" + pfad.name)
    return Sammlung(seiten=[s], start=s, herkunft=str(pfad), gesamt=1)


def _hole(url: str, timeout: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (http(s) wird unten geprüft)
        roh = r.read(4_000_000)
        ct = r.headers.get_content_charset() or "utf-8"
    return roh.decode(ct, errors="replace")


def aus_url(url: str, timeout: float = 10.0, tiefe: int = 2) -> Sammlung:
    """Startseite holen, dann den Links folgen – bis `tiefe` Klicks.

    Wir crawlen absichtlich nur so tief, wie die Rechtsprechung erlaubt
    (BGH I ZR 228/03: zwei Klicks). Was tiefer liegt, ist ohnehin nicht
    "unmittelbar erreichbar" im Sinne von § 5 Abs. 1 DDG.
    """
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"Nur http(s) wird geholt, nicht: {url}")

    basis = urllib.parse.urlparse(url).netloc
    gesehen: dict[str, Seite] = {}
    grenze = [url]

    for _ in range(tiefe + 1):
        naechste: list[str] = []
        for u in grenze:
            u, _ = urllib.parse.urldefrag(u)
            if u in gesehen or len(gesehen) >= MAX_SEITEN:
                continue
            try:
                s = parse(_hole(u, timeout), url=u)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
                continue
            gesehen[u] = s
            for lnk in s.links:
                ziel = urllib.parse.urljoin(u, lnk.href)
                p = urllib.parse.urlparse(ziel)
                # Nur dieselbe Domain, nur http(s). Das Impressum eines
                # fremden Anbieters ist nicht das eigene.
                if p.scheme in ("http", "https") and p.netloc == basis:
                    naechste.append(ziel)
        grenze = naechste

    seiten = list(gesehen.values())
    return Sammlung(seiten=seiten, start=gesehen.get(url), herkunft=url, gesamt=len(seiten))


def laden(ziel: str, timeout: float = 10.0) -> Sammlung:
    """URL, Datei oder Ordner – das Werkzeug entscheidet selbst."""
    if ziel.startswith(("http://", "https://")):
        return aus_url(ziel, timeout=timeout)
    p = Path(ziel)
    if p.is_dir():
        return aus_ordner(p)
    if p.is_file():
        return aus_datei(p)
    raise FileNotFoundError(f"Weder URL noch Datei noch Ordner: {ziel}")
