"""HTML zu Text und Links — mit der stdlib, ohne Abhängigkeiten.

Wir brauchen genau zwei Dinge aus einer Seite: den sichtbaren Text (darin
stehen die Pflichtangaben) und die Links (daran hängt die Erreichbarkeit).
Beides leistet `html.parser`. beautifulsoup4 würde hier nichts hinzufügen,
was den Preis einer Abhängigkeit wert wäre.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

# Inhalte, die der Nutzer nie sieht. Ein Impressum, das nur im <script>-Block
# steht, ist kein Impressum – deshalb fliegen diese Bereiche raus, bevor
# irgendeine Prüfung sie zu Gesicht bekommt.
UNSICHTBAR = {"script", "style", "template", "noscript", "svg", "head"}

# Tags, die im gerenderten Text einen Umbruch erzeugen. Ohne das klebt
# "Musterstraße 1" an "12345 Musterstadt" – oder schlimmer: es klebt nicht,
# und eine über zwei <br> verteilte Anschrift wird nicht mehr erkannt.
BLOCK = {
    "p", "div", "br", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5",
    "h6", "section", "article", "header", "footer", "address", "blockquote",
    "ul", "ol", "dl", "dt", "dd", "table", "main", "nav", "hr", "form",
}


@dataclass
class Link:
    """Ein Link mit dem, was drumherum steht."""

    href: str
    text: str
    #: True, wenn der Link in einem <footer> oder <nav> steht. Die
    #: Rechtsprechung verlangt "leicht erkennbar" – der Footer ist der Ort,
    #: an dem ein durchschnittlicher Nutzer das Impressum sucht.
    im_footer: bool = False


@dataclass
class Seite:
    """Eine geparste HTML-Seite."""

    url: str
    text: str = ""
    links: list[Link] = field(default_factory=list)
    titel: str = ""
    #: Roh-HTML, für Prüfungen, die Markup brauchen (z. B. mailto:-Links).
    html: str = ""

    def enthaelt(self, *muster: str) -> bool:
        """Kommt eines der Muster (Regex, case-insensitive) im Text vor?"""
        return any(re.search(m, self.text, re.I) for m in muster)


class _Sammler(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._teile: list[str] = []
        self._ignorieren = 0
        self._tiefe_footer = 0
        self._in_titel = False
        self._link: tuple[str, list[str]] | None = None
        self.titel = ""
        self.links: list[Link] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if tag in UNSICHTBAR:
            self._ignorieren += 1
            return
        if tag == "title":
            self._in_titel = True
        if tag in ("footer", "nav"):
            self._tiefe_footer += 1
        # Auch ein <div class="footer"> ist ein Footer. Nicht jede Seite ist
        # semantisch sauber ausgezeichnet, und die Prüfung soll die Realität
        # abbilden, nicht die Spezifikation.
        elif re.search(r"footer|impressum|legal|rechtlich", str(d.get("class", "")) + str(d.get("id", "")), re.I):
            self._tiefe_footer += 1
            self._teile.append("\x00FOOTER\x00")  # Marker, s. handle_endtag
        if tag in BLOCK:
            self._teile.append("\n")
        if tag == "a":
            self._link = (d.get("href") or "", [])
        # alt-Texte zählen als sichtbarer Text: ein Impressum-Link kann ein Bild sein.
        if tag == "img" and d.get("alt"):
            self._teile.append(f" {d['alt']} ")

    def handle_endtag(self, tag: str) -> None:
        if tag in UNSICHTBAR:
            self._ignorieren = max(0, self._ignorieren - 1)
            return
        if tag == "title":
            self._in_titel = False
        if tag in ("footer", "nav"):
            self._tiefe_footer = max(0, self._tiefe_footer - 1)
        if tag in BLOCK:
            self._teile.append("\n")
        if tag == "a" and self._link is not None:
            href, stuecke = self._link
            self.links.append(
                Link(
                    href=href.strip(),
                    text=" ".join("".join(stuecke).split()),
                    im_footer=self._tiefe_footer > 0,
                )
            )
            self._link = None

    def handle_data(self, data: str) -> None:
        # Der <title> steht im <head>, und der <head> ist unsichtbar. Erst den
        # Titel einsammeln, dann erst abbrechen – sonst bleibt er immer leer.
        if self._in_titel:
            self.titel += data
        if self._ignorieren:
            return
        # Zeilenumbrüche im Quelltext sind Formatierung, keine Struktur: ein im
        # Editor umbrochener Absatz darf nicht in zwei Zeilen zerfallen, sonst
        # findet keine Prüfung mehr "Einschränkung der Verarbeitung", nur noch
        # "Einschränkung" und "der Verarbeitung". Nur Block-Tags brechen um.
        self._teile.append(re.sub(r"\s+", " ", data))
        if self._link is not None:
            self._link[1].append(data)

    def text(self) -> str:
        roh = "".join(self._teile).replace("\x00FOOTER\x00", "")
        # Zeilen einzeln normalisieren: Whitespace in der Zeile kollabieren,
        # aber die Zeilenstruktur erhalten – die Anschrift lebt davon.
        zeilen = [" ".join(z.split()) for z in roh.split("\n")]
        return "\n".join(z for z in zeilen if z)


def parse(html: str, url: str = "") -> Seite:
    p = _Sammler()
    p.feed(html)
    p.close()
    return Seite(
        url=url,
        text=p.text(),
        links=p.links,
        titel=" ".join(p.titel.split()),
        html=html,
    )
