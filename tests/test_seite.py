"""Ganze Seiten: Auffinden, Erreichbarkeit, Exit-Code, Parser."""

from __future__ import annotations

from pathlib import Path

from impressumcheck import Grad, parse, pruefe_alles
from impressumcheck.cli import main
from impressumcheck.quellen import laden

FIXTURES = Path(__file__).parent / "fixtures"


def grade(ordner: str) -> dict[str, Grad]:
    sm = laden(str(FIXTURES / ordner))
    return {b.regel: b.grad for b in pruefe_alles(sm)}


# --- Auffinden --------------------------------------------------------------

def test_korrekte_seite_besteht_vollstaendig():
    g = grade("seite-korrekt")
    assert [r for r, v in g.items() if v is Grad.FEHLER] == []


def test_fehlendes_impressum_wird_gefunden():
    g = grade("seite-ohne-impressum")
    assert g["I-GEFUNDEN"] is Grad.FEHLER
    # Die Datenschutzerklärung ist da und in Ordnung — das eine sagt nichts
    # über das andere.
    assert g["D-GEFUNDEN"] is Grad.OK


# --- Erreichbarkeit (§ 5 Abs. 1 DDG, BGH I ZR 228/03) -----------------------

def test_impressum_muss_von_jeder_seite_erreichbar_sein():
    g = grade("seite-versteckt")
    # Das Impressum ist inhaltlich tadellos …
    assert g["I-ANSCHRIFT"] is Grad.OK
    # … aber von /tief.html führt kein Link dorthin.
    assert g["I-ERREICHBAR"] is Grad.FEHLER


def test_erreichbarkeit_ok_wenn_footer_ueberall():
    assert grade("seite-korrekt")["I-ERREICHBAR"] is Grad.OK


def test_erreichbarkeitsbefund_nennt_die_seite_ohne_link():
    sm = laden(str(FIXTURES / "seite-versteckt"))
    b = [x for x in pruefe_alles(sm) if x.regel == "I-ERREICHBAR"][0]
    assert "/tief.html" in b.beleg


# --- Exit-Codes (das ist der Zweck des Werkzeugs) ---------------------------

def test_exit_0_bei_korrekter_seite(capsys):
    assert main([str(FIXTURES / "seite-korrekt")]) == 0


def test_exit_1_bei_fehlendem_impressum(capsys):
    assert main([str(FIXTURES / "seite-ohne-impressum")]) == 1


def test_exit_1_bei_unerreichbarem_impressum(capsys):
    assert main([str(FIXTURES / "seite-versteckt")]) == 1


def test_streng_macht_warnungen_zu_fehlern(capsys):
    # nur-email.html löst genau eine Warnung aus (kein zweiter Kommunikationsweg)
    # und keinen Fehler.
    datei = str(FIXTURES / "impressum" / "nur-email.html")
    assert main([datei, "--kein-exit-code"]) == 0
    assert main([datei, "--streng"]) == 1


def test_kein_exit_code_bricht_nie(capsys):
    assert main([str(FIXTURES / "seite-ohne-impressum"), "--kein-exit-code"]) == 0


def test_json_ausgabe_ist_gueltiges_json(capsys):
    import json
    main([str(FIXTURES / "seite-korrekt"), "--json"])
    d = json.loads(capsys.readouterr().out)
    assert d["geprüfte_seiten"] == 4
    assert any(b["regel"] == "I-ANSCHRIFT" for b in d["befunde"])


def test_ausgabe_nennt_immer_die_grenze(capsys):
    # Der Haftungsausschluss steht in JEDER Ausgabe, nicht nur im README.
    # Ein grünes Häkchen ohne diesen Satz ist gefährlicher als ein rotes Kreuz.
    main([str(FIXTURES / "seite-korrekt")])
    aus = capsys.readouterr().out
    assert "nicht, ob sie STIMMEN" in aus
    assert "keine Rechtsberatung" in aus


def test_unbekanntes_ziel_gibt_exit_2(capsys):
    assert main(["/gibt/es/nicht"]) == 2


# --- Auffinden über den Titel ----------------------------------------------

def test_einzelne_datei_wird_am_titel_erkannt():
    # `impressum-check postfach.html`: der Dateiname sagt nichts, der <title>
    # sagt "Impressum". Wer das Werkzeug direkt auf eine Datei stößt, hat die
    # Frage nach dem Auffinden bereits beantwortet.
    sm = laden(str(FIXTURES / "impressum" / "postfach.html"))
    g = {b.regel: b.grad for b in pruefe_alles(sm)}
    assert g["I-GEFUNDEN"] is Grad.OK
    assert g["I-POSTFACH"] is Grad.FEHLER


def test_pfad_hat_vorrang_vor_titel():
    sm = laden(str(FIXTURES / "seite-korrekt"))
    imp = sm.finde("impressum", "imprint")
    assert imp is not None and imp.url == "/impressum.html"


# --- Ehrlichkeit über den eigenen Umfang ------------------------------------

def test_stichprobe_wird_gemeldet():
    # Ein Prüfer, der verschweigt, dass er nur einen Teil gesehen hat,
    # ist ein Alibi. Bei Deckelung muss ein HINWEIS erscheinen.
    from impressumcheck.quellen import Sammlung
    sm = laden(str(FIXTURES / "seite-korrekt"))
    gedeckelt = Sammlung(seiten=sm.seiten, start=sm.start, herkunft=sm.herkunft, gesamt=9999)
    hinweise = [b for b in pruefe_alles(gedeckelt) if b.regel == "STICHPROBE"]
    assert len(hinweise) == 1
    assert "9999" in hinweise[0].text


def test_kein_stichprobenhinweis_wenn_alles_geprueft():
    sm = laden(str(FIXTURES / "seite-korrekt"))
    assert not [b for b in pruefe_alles(sm) if b.regel == "STICHPROBE"]


# --- Parser -----------------------------------------------------------------

def test_script_inhalt_zaehlt_nicht_als_impressum():
    # Ein Impressum, das nur im JavaScript steht, sieht kein Nutzer.
    s = parse('<script>var i = "Musterstraße 1, 10115 Berlin";</script><p>Nichts.</p>')
    assert "Musterstraße" not in s.text


def test_anschrift_ueber_br_getrennt_wird_erkannt():
    s = parse("<address>Firma<br>Musterstraße 12<br>10115 Berlin</address>")
    assert "Musterstraße 12" in s.text
    assert "10115 Berlin" in s.text
    # ohne die <br>-Behandlung stünde hier "Musterstraße 1210115 Berlin"
    assert "1210115" not in s.text
