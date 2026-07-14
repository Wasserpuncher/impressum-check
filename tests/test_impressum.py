"""Die Pflichtangaben nach § 5 DDG — jeder Fehlerfall ein Test.

Und zu jedem Fehlerfall der ehrliche Fall, mit dem er nicht verwechselt
werden darf. Ein Prüfer, der bei allem anschlägt, prüft nichts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from impressumcheck import Grad, parse
from impressumcheck.quellen import Sammlung
from impressumcheck.regeln import pruefe_impressum

FIXTURES = Path(__file__).parent / "fixtures" / "impressum"


def lade(name: str):
    seite = parse((FIXTURES / name).read_text(encoding="utf-8"), url=f"/{name}")
    return Sammlung(seiten=[seite], start=seite, herkunft=name), seite


def befund(name: str, regel: str):
    sm, s = lade(name)
    for b in pruefe_impressum(sm, s):
        if b.regel == regel:
            return b
    raise AssertionError(f"Regel {regel} lieferte keinen Befund für {name}")


# --- das korrekte Impressum: nichts darf anschlagen -------------------------

def test_korrektes_gmbh_impressum_hat_keine_fehler():
    sm, s = lade("korrekt-gmbh.html")
    fehler = [b for b in pruefe_impressum(sm, s) if b.grad is Grad.FEHLER]
    assert fehler == [], f"Falsch-positiv: {[b.regel for b in fehler]}"


@pytest.mark.parametrize("regel", [
    "I-ANSCHRIFT", "I-EMAIL", "I-ZWEITER-WEG", "I-VERTRETER", "I-REGISTER", "I-USTID",
])
def test_korrektes_impressum_besteht_jede_einzelpruefung(regel):
    assert befund("korrekt-gmbh.html", regel).grad is Grad.OK


# --- § 5 Abs. 1 Nr. 1: Anschrift -------------------------------------------

def test_fehlende_anschrift_ist_ein_fehler():
    b = befund("ohne-anschrift.html", "I-ANSCHRIFT")
    assert b.grad is Grad.FEHLER
    assert "§ 5 Abs. 1 DDG Nr. 1" in b.norm


def test_postfach_ist_keine_ladungsfaehige_anschrift():
    # Der wichtigste Test der Datei: hier steht eine Adresse, und sie ist
    # trotzdem falsch. Eine Prüfung auf "PLZ vorhanden" würde das durchwinken.
    b = befund("postfach.html", "I-POSTFACH")
    assert b.grad is Grad.FEHLER
    assert "Postfach" in b.text


def test_postfach_wird_nicht_als_anschrift_gezaehlt():
    sm, s = lade("postfach.html")
    regeln = {b.regel for b in pruefe_impressum(sm, s) if b.grad is Grad.OK}
    assert "I-ANSCHRIFT" not in regeln


def test_strasse_neben_postfach_ist_in_ordnung():
    # Wer BEIDES angibt — Hausanschrift und Postfach — erfüllt die Pflicht.
    # Das Postfach ist dann eine Zusatzangabe, kein Mangel.
    html = """<h1>Impressum</h1><p>Beide GmbH<br>Hauptstraße 5<br>10115 Berlin<br>
              Postfach 11 22 33<br>10001 Berlin</p>
              <p>Geschäftsführer: A. B.</p><p>Tel: +49 30 1<br>a@b.de</p>
              <p>Amtsgericht Berlin, HRB 1234</p>"""
    s = parse(html, url="/impressum")
    sm = Sammlung(seiten=[s], start=s)
    grade = {b.regel: b.grad for b in pruefe_impressum(sm, s)}
    assert grade["I-ANSCHRIFT"] is Grad.OK
    assert "I-POSTFACH" not in grade


# --- § 5 Abs. 1 Nr. 2: E-Mail und zweiter Kommunikationsweg -----------------

def test_fehlende_email_ist_ein_fehler():
    s = parse("<h1>Impressum</h1><p>Max Mustermann<br>Musterweg 1<br>10115 Berlin</p>", url="/impressum")
    sm = Sammlung(seiten=[s], start=s)
    b = [x for x in pruefe_impressum(sm, s) if x.regel == "I-EMAIL"][0]
    assert b.grad is Grad.FEHLER


def test_nur_email_ohne_zweiten_weg_ist_eine_warnung():
    # EuGH C-298/07: die E-Mail allein genügt nicht.
    b = befund("nur-email.html", "I-ZWEITER-WEG")
    assert b.grad is Grad.WARNUNG
    assert "C-298/07" in b.norm


def test_kontaktformular_genuegt_als_zweiter_weg():
    # Ebenfalls EuGH C-298/07: eine Telefonnummer ist NICHT zwingend.
    # Ein Prüfer, der sie verlangt, zitiert ein Urteil, das es nicht gibt.
    html = """<h1>Impressum</h1><p>Clara Einsam<br>Seeweg 2<br>18055 Rostock</p>
              <p>E-Mail: clara@einsam.de</p><a href="/kontakt">Kontakt</a>"""
    s = parse(html, url="/impressum")
    sm = Sammlung(seiten=[s], start=s)
    b = [x for x in pruefe_impressum(sm, s) if x.regel == "I-ZWEITER-WEG"][0]
    assert b.grad is Grad.OK


def test_mailto_link_zaehlt_als_email():
    s = parse('<h1>Impressum</h1><p>Weg 1<br>10115 Berlin</p><a href="mailto:x@y.de">Mail</a>', url="/impressum")
    sm = Sammlung(seiten=[s], start=s)
    b = [x for x in pruefe_impressum(sm, s) if x.regel == "I-EMAIL"][0]
    assert b.grad is Grad.OK


# --- § 5 Abs. 1 Nr. 1 + Nr. 4: Rechtsform, Vertreter, Register --------------

def test_gmbh_ohne_registerangaben_ist_ein_fehler():
    b = befund("gmbh-ohne-register.html", "I-REGISTER")
    assert b.grad is Grad.FEHLER
    assert "Nr. 4" in b.norm


def test_gmbh_ohne_geschaeftsfuehrer_ist_ein_fehler():
    b = befund("gmbh-ohne-geschaeftsfuehrer.html", "I-VERTRETER")
    assert b.grad is Grad.FEHLER


def test_einzelunternehmer_braucht_kein_handelsregister():
    # Die Kehrseite: eine natürliche Person ohne Rechtsformzusatz muss kein
    # Register nennen. Wer das verlangt, erfindet eine Pflicht.
    sm, s = lade("nur-email.html")
    regeln = {b.regel for b in pruefe_impressum(sm, s)}
    assert "I-REGISTER" not in regeln
    assert "I-VERTRETER" not in regeln


# --- § 5 Abs. 1 Nr. 6: USt-IdNr. -------------------------------------------

def test_kaputte_ustid_ist_ein_fehler():
    b = befund("ustid-kaputt.html", "I-USTID")
    assert b.grad is Grad.FEHLER
    assert "9 Ziffern" in b.text


def test_kaputte_ustid_wird_zitiert():
    # Die Meldung muss die Nummer nennen, die dasteht. Ein Prüfer, der
    # "kein Wert gefunden" sagt, während der Wert danebensteht, schickt den
    # Leser auf die Suche nach einem Fehler, den er schon gefunden hat.
    b = befund("ustid-kaputt.html", "I-USTID")
    assert "DE1234567" in b.text
    assert "7 Ziffern" in b.text


def test_fehlende_ustid_ist_kein_fehler():
    # § 5 Abs. 1 Nr. 6 DDG: "sofern vorhanden". Wer keine hat, muss keine nennen.
    sm, s = lade("ohne-anschrift.html")
    assert "I-USTID" not in {b.regel for b in pruefe_impressum(sm, s)}


def test_ustid_mit_leerzeichen_ist_gueltig():
    # "DE 123 456 789" ist dieselbe Nummer. Formatierung ist kein Mangel.
    html = """<h1>Impressum</h1><p>Weg 1<br>10115 Berlin</p><p>a@b.de</p>
              <p>USt-IdNr.: DE 123 456 789</p>"""
    s = parse(html, url="/impressum")
    sm = Sammlung(seiten=[s], start=s)
    b = [x for x in pruefe_impressum(sm, s) if x.regel == "I-USTID"][0]
    assert b.grad is Grad.OK


# --- Das abgelöste Gesetz ---------------------------------------------------

def test_zitat_von_paragraf_5_tmg_wird_bemaengelt():
    # Das TMG wurde am 14.05.2024 durch das DDG abgelöst.
    b = befund("tmg-veraltet.html", "I-TMG-VERALTET")
    assert b.grad is Grad.WARNUNG
    assert "DDG" in b.text


def test_zitat_von_paragraf_5_ddg_wird_nicht_bemaengelt():
    sm, s = lade("korrekt-gmbh.html")
    assert "I-TMG-VERALTET" not in {b.regel for b in pruefe_impressum(sm, s)}
