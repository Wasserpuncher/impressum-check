"""Art. 13 DSGVO — die Informationspflichten in der Datenschutzerklärung."""

from __future__ import annotations

from pathlib import Path

import pytest

from impressumcheck import Grad, parse
from impressumcheck.regeln import pruefe_datenschutz

FIXTURES = Path(__file__).parent / "fixtures" / "datenschutz"


def befunde(name: str):
    s = parse((FIXTURES / name).read_text(encoding="utf-8"), url=f"/{name}")
    return {b.regel: b for b in pruefe_datenschutz(s)}


def test_korrekte_datenschutzerklaerung_hat_keine_fehler():
    fehler = [b.regel for b in befunde("korrekt.html").values() if b.grad is Grad.FEHLER]
    assert fehler == []


@pytest.mark.parametrize("regel", [
    "D-VERANTWORTLICHER", "D-BETROFFENENRECHTE", "D-BESCHWERDE",
    "D-RECHTSGRUNDLAGE", "D-SPEICHERDAUER",
])
def test_korrekte_erklaerung_besteht_jede_einzelpruefung(regel):
    assert befunde("korrekt.html")[regel].grad is Grad.OK


def test_fehlender_verantwortlicher_ist_ein_fehler():
    # Das ist die Regel, an der layer8 seinen Astro-Build abbricht
    # (src/pages/datenschutz.astro). Hier ist sie als Prüfung.
    b = befunde("ohne-verantwortlichen.html")["D-VERANTWORTLICHER"]
    assert b.grad is Grad.FEHLER
    assert b.norm == "Art. 13 Abs. 1 lit. a DSGVO"


def test_verantwortlicher_ohne_kontakt_ist_ein_fehler():
    # Art. 13 Abs. 1 lit. a verlangt Name UND Kontaktdaten. Ein Name allein
    # ist eine Behauptung, keine Erreichbarkeit.
    s = parse("<h1>Datenschutz</h1><p>Verantwortlicher ist die Beispiel GmbH.</p>", url="/datenschutz")
    b = {x.regel: x for x in pruefe_datenschutz(s)}["D-VERANTWORTLICHER"]
    assert b.grad is Grad.FEHLER
    assert "Kontaktdaten" in b.text


def test_fehlendes_beschwerderecht_ist_ein_fehler():
    b = befunde("ohne-beschwerderecht.html")["D-BESCHWERDE"]
    assert b.grad is Grad.FEHLER
    assert b.norm == "Art. 13 Abs. 2 lit. d DSGVO"


def test_fehlende_betroffenenrechte_sind_ein_fehler():
    s = parse("<h1>Datenschutz</h1><p>Verantwortlich: A. B., a@b.de</p>", url="/datenschutz")
    b = {x.regel: x for x in pruefe_datenschutz(s)}["D-BETROFFENENRECHTE"]
    assert b.grad is Grad.FEHLER


def test_unvollstaendige_betroffenenrechte_sind_nur_eine_warnung():
    # Fünf von sechs Rechten: das ist ein Mangel, aber kein leeres Blatt.
    # Der Unterschied gehört in den Grad, nicht in den Exit-Code.
    s = parse("""<h1>Datenschutz</h1><p>Verantwortlicher: A. B., a@b.de</p>
                 <p>Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung,
                 Widerspruch. Beschwerde bei der Aufsichtsbehörde möglich.</p>""",
              url="/datenschutz")
    b = {x.regel: x for x in pruefe_datenschutz(s)}["D-BETROFFENENRECHTE"]
    assert b.grad is Grad.WARNUNG
    assert "Datenübertragbarkeit" in b.text
