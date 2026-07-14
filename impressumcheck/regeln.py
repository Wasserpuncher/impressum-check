"""Die Pflichtangaben — als Code.

Jede Regel nennt die Norm, auf die sie sich stützt. Eine Prüfung ohne
Fundstelle ist eine Meinung, und Meinungen gehören nicht in einen Exit-Code.

Was hier NICHT geprüft wird, steht im README ganz oben: ob die Angaben
*stimmen*. Eine erfundene Anschrift besteht jede dieser Regeln. Das Werkzeug
prüft Vollständigkeit, nicht Wahrheit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .parse import Seite
from .quellen import Sammlung


class Grad(Enum):
    """Wie schlimm ist es?"""

    FEHLER = "FEHLER"      # Pflichtangabe fehlt → Exit 1
    WARNUNG = "WARNUNG"    # verdächtig, aber es kann Gründe geben → Exit 1 nur mit --streng
    HINWEIS = "HINWEIS"    # rein informativ
    OK = "OK"


@dataclass
class Befund:
    regel: str
    grad: Grad
    norm: str          # die Rechtsgrundlage, wörtlich zitierbar
    text: str
    seite: str = ""
    beleg: str = ""    # die Fundstelle im Dokument, falls es eine gibt

    @property
    def zaehlt_als_fehler(self) -> bool:
        return self.grad is Grad.FEHLER


# ---------------------------------------------------------------------------
# Bausteine: die Muster, an denen die Pflichtangaben erkannt werden.
# ---------------------------------------------------------------------------

# Straße + Hausnummer. Deutsche Straßennamen enden auf -straße/-str./-weg/
# -allee/-platz/-gasse/-ring/-damm/-ufer, oder es ist "Am Markt 3".
RE_STRASSE = re.compile(
    r"""(?:
        [A-ZÄÖÜ][\wÄÖÜäöüß.\-]*
        (?:stra(?:ss|ß)e|str\.|weg|allee|platz|gasse|ring|damm|ufer|chaussee|hof)
        |^(?:Am|An\ der|Auf\ dem|Zum|Zur|In\ der|Beim)\ [A-ZÄÖÜ][\wÄÖÜäöüß\-]+
    )
    \s*\d+\s*[a-zA-Z]?          # Hausnummer, optional mit Buchstabe
    """,
    re.X | re.M,
)

# PLZ + Ort: fünf Ziffern, dann ein großgeschriebener Ortsname.
RE_PLZ_ORT = re.compile(r"\b(?<!\d)(\d{5})(?!\d)\s+([A-ZÄÖÜ][\wÄÖÜäöüß.\-]+(?:\s+[A-ZÄÖÜ][\wÄÖÜäöüß.\-]+)*)")

# Postfach — ausdrücklich KEINE ladungsfähige Anschrift.
RE_POSTFACH = re.compile(r"\bPostfach\b|\bPost(?:\s|-)?box\b|\bP\.?\s?O\.?\s?Box\b", re.I)

RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Auch obfuskierte Adressen zählen: "kai (at) example.de" ist erreichbar.
RE_EMAIL_UMSCHRIEBEN = re.compile(r"[A-Za-z0-9._%+\-]+\s*[\(\[]\s*(?:at|ät)\s*[\)\]]\s*[A-Za-z0-9.\-]+\s*[\(\[]?\s*(?:dot|punkt)?\s*[\)\]]?\s*\.?\s*[A-Za-z]{2,}", re.I)

# Telefonnummer: +49… / 0… mit mindestens sechs Ziffern insgesamt.
RE_TELEFON = re.compile(r"(?:Tel(?:efon)?\.?|Fon|Mobil|Ruf)\s*:?\s*((?:\+49|0)[\d\s/().\-]{6,})", re.I)

# Rechtsformen, die zwingend Register + Vertreter nach sich ziehen.
RE_KAPITALGESELLSCHAFT = re.compile(
    r"\b(?:GmbH(?:\s*&\s*Co\.?\s*KG)?|UG\s*\(haftungsbeschränkt\)|UG\b|gGmbH|AG\b|KGaA|SE\b|e\.?\s?G\.?\b)",
)
RE_REGISTERGERICHT = re.compile(r"(?:Registergericht|Amtsgericht|Handelsregister(?:\s*(?:beim|des|Nr))?|Register(?:nummer|gericht))", re.I)
RE_REGISTERNUMMER = re.compile(r"\b(HRA|HRB|GnR|PR|VR)\s*[:\-]?\s*(\d{1,7})\s*([A-Z]{0,2})\b", re.I)
RE_VERTRETER = re.compile(
    r"(?:Gesch[äa]ftsf[üu]hrer(?:in)?|Vorstand|Vertretungsberechtigt|vertreten\s+durch|Inhaber(?:in)?|Vorstandsvorsitzende)",
    re.I,
)

# USt-IdNr.: DE + 9 Ziffern (§ 27a UStG). Wir prüfen das Format, nicht die Existenz.
RE_USTID_LABEL = re.compile(r"(?:Umsatzsteuer[-\s]?Identifikationsnummer|USt[-\.\s]?IdNr\.?|Ust[-\.\s]?Id|VAT[-\s]?ID|USt[-\s]?ID)", re.I)
# Absichtlich großzügig: die Nummer wird eingefangen, wie sie dasteht — auch eine
# zu kurze. Die Länge wird danach geprüft. Ein Muster, das nur gültige Nummern
# findet, kann eine ungültige nicht zitieren und meldet "kein Wert gefunden",
# obwohl der Wert direkt daneben steht.
RE_USTID_WERT = re.compile(r"\bDE[ .\-]?(\d(?:[\d ]*\d)?)")

# Das abgelöste Gesetz. Seit 14.05.2024 heißt es DDG.
RE_TMG = re.compile(r"§\s*5\s*(?:Abs\.?\s*\d\s*)?TMG|Telemediengesetz|nach\s+§\s*5\s*TMG", re.I)


def _erstes(muster: re.Pattern[str], text: str) -> str:
    m = muster.search(text)
    return m.group(0).strip() if m else ""


def _hat_email(s: Seite) -> str:
    if m := RE_EMAIL.search(s.text):
        return m.group(0)
    if "mailto:" in s.html.lower():
        return "mailto:-Link"
    if m := RE_EMAIL_UMSCHRIEBEN.search(s.text):
        return m.group(0)
    return ""


def _hat_kontaktformular(sm: Sammlung, s: Seite) -> str:
    if re.search(r"<form\b", s.html, re.I):
        return "Formular auf der Impressumsseite"
    for lnk in s.links:
        if re.search(r"kontakt|contact", lnk.href + " " + lnk.text, re.I):
            return f"Link „{lnk.text or lnk.href}“"
    if sm.finde("/kontakt", "/contact"):
        return "Kontaktseite vorhanden"
    return ""


# ---------------------------------------------------------------------------
# Die Regeln
# ---------------------------------------------------------------------------

def pruefe_impressum(sm: Sammlung, s: Seite) -> list[Befund]:
    """§ 5 Abs. 1 DDG — die Pflichtangaben, Nummer für Nummer."""
    b: list[Befund] = []
    N = "§ 5 Abs. 1 DDG"

    # --- Nr. 1: Name und Anschrift ---------------------------------------
    strasse = _erstes(RE_STRASSE, s.text)
    plz = RE_PLZ_ORT.search(s.text)
    postfach = RE_POSTFACH.search(s.text)

    if strasse and plz:
        b.append(Befund("I-ANSCHRIFT", Grad.OK, f"{N} Nr. 1",
                        "Anschrift gefunden (Straße, Hausnummer, PLZ, Ort).",
                        s.url, f"{strasse}, {plz.group(0)}"))
    elif postfach and not strasse:
        # Das ist der interessante Fehlerfall: formal steht eine Adresse da,
        # sie ist nur nicht ladungsfähig.
        b.append(Befund("I-POSTFACH", Grad.FEHLER, f"{N} Nr. 1",
                        "Nur ein Postfach angegeben. § 5 Abs. 1 Nr. 1 DDG verlangt die Anschrift, "
                        "unter der der Anbieter niedergelassen ist — ein Postfach ist keine "
                        "ladungsfähige Anschrift.",
                        s.url, postfach.group(0)))
    else:
        fehlt = []
        if not strasse:
            fehlt.append("Straße + Hausnummer")
        if not plz:
            fehlt.append("PLZ + Ort")
        b.append(Befund("I-ANSCHRIFT", Grad.FEHLER, f"{N} Nr. 1",
                        f"Keine vollständige Anschrift erkannt (es fehlt: {', '.join(fehlt)}).",
                        s.url))

    # --- Nr. 2: E-Mail und ein zweiter Kommunikationsweg ------------------
    # EuGH C-298/07: die E-Mail allein genügt nicht, eine Telefonnummer ist
    # aber nicht zwingend — ein Kontaktformular reicht als zweiter Weg.
    email = _hat_email(s)
    if email:
        b.append(Befund("I-EMAIL", Grad.OK, f"{N} Nr. 2", "E-Mail-Adresse gefunden.", s.url, email))
    else:
        b.append(Befund("I-EMAIL", Grad.FEHLER, f"{N} Nr. 2",
                        "Keine E-Mail-Adresse gefunden. § 5 Abs. 1 Nr. 2 DDG nennt sie ausdrücklich.",
                        s.url))

    telefon = _erstes(RE_TELEFON, s.text)
    formular = _hat_kontaktformular(sm, s)
    if telefon:
        b.append(Befund("I-ZWEITER-WEG", Grad.OK, f"{N} Nr. 2 / EuGH C-298/07",
                        "Zweiter Kommunikationsweg: Telefonnummer.", s.url, telefon))
    elif formular:
        b.append(Befund("I-ZWEITER-WEG", Grad.OK, f"{N} Nr. 2 / EuGH C-298/07",
                        "Zweiter Kommunikationsweg: Kontaktformular (nach EuGH C-298/07 zulässig).",
                        s.url, formular))
    else:
        b.append(Befund("I-ZWEITER-WEG", Grad.WARNUNG, f"{N} Nr. 2 / EuGH C-298/07",
                        "Nur E-Mail, kein zweiter Kommunikationsweg erkannt. Der EuGH (C-298/07) "
                        "verlangt neben der E-Mail einen weiteren Weg zur „unmittelbaren und "
                        "effizienten Kommunikation“ — Telefon oder Kontaktformular.",
                        s.url))

    # --- Nr. 1 + Nr. 4: Rechtsform → Vertreter, Register, Registernummer ---
    rf = RE_KAPITALGESELLSCHAFT.search(s.text)
    if rf:
        form = rf.group(0)
        if not RE_VERTRETER.search(s.text):
            b.append(Befund("I-VERTRETER", Grad.FEHLER, f"{N} Nr. 1",
                            f"„{form}“ genannt, aber kein Vertretungsberechtigter. Bei juristischen "
                            "Personen verlangt § 5 Abs. 1 Nr. 1 DDG die Angabe der Vertretungsberechtigten "
                            "(z. B. Geschäftsführer, Vorstand).",
                            s.url, form))
        else:
            b.append(Befund("I-VERTRETER", Grad.OK, f"{N} Nr. 1",
                            "Vertretungsberechtigter genannt.", s.url, _erstes(RE_VERTRETER, s.text)))

        nr = RE_REGISTERNUMMER.search(s.text)
        gericht = RE_REGISTERGERICHT.search(s.text)
        if nr and gericht:
            b.append(Befund("I-REGISTER", Grad.OK, f"{N} Nr. 4",
                            "Register und Registernummer gefunden.", s.url,
                            f"{gericht.group(0)}, {nr.group(0)}"))
        else:
            fehlt = []
            if not gericht:
                fehlt.append("Registergericht")
            if not nr:
                fehlt.append("Registernummer (HRB/HRA/…)")
            b.append(Befund("I-REGISTER", Grad.FEHLER, f"{N} Nr. 4",
                            f"„{form}“ genannt, aber es fehlt: {', '.join(fehlt)}. § 5 Abs. 1 Nr. 4 DDG "
                            "verlangt Handelsregister und Registernummer.",
                            s.url, form))

    # --- Nr. 6: USt-IdNr. --------------------------------------------------
    # Pflicht nur, "sofern vorhanden". Wir prüfen deshalb nur das Format —
    # das Fehlen ist kein Fehler, ein kaputtes Format schon.
    if RE_USTID_LABEL.search(s.text):
        m = RE_USTID_WERT.search(s.text)
        ziffern = re.sub(r"\D", "", m.group(1)) if m else ""
        if m and len(ziffern) == 9:
            b.append(Befund("I-USTID", Grad.OK, f"{N} Nr. 6 / § 27a UStG",
                            "USt-IdNr. angegeben, Format gültig (DE + 9 Ziffern).",
                            s.url, f"DE{ziffern}"))
        elif m:
            b.append(Befund("I-USTID", Grad.FEHLER, f"{N} Nr. 6 / § 27a UStG",
                            f"USt-IdNr. „{m.group(0).strip()}“ hat {len(ziffern)} Ziffern. Eine "
                            "deutsche USt-IdNr. besteht aus „DE“ und genau 9 Ziffern (§ 27a UStG).",
                            s.url, m.group(0).strip()))
        else:
            b.append(Befund("I-USTID", Grad.FEHLER, f"{N} Nr. 6 / § 27a UStG",
                            "Eine USt-IdNr. wird angekündigt, aber es folgt keine Nummer im "
                            "Format „DE“ + 9 Ziffern.",
                            s.url))

    # --- Das Gesetz selbst -------------------------------------------------
    # Kein Fehler (die Norm muss gar nicht zitiert werden), aber ein starkes
    # Indiz dafür, dass das Impressum seit Mai 2024 niemand mehr angesehen hat.
    if RE_TMG.search(s.text):
        b.append(Befund("I-TMG-VERALTET", Grad.WARNUNG, "DDG, in Kraft seit 14.05.2024",
                        "Das Impressum beruft sich auf das TMG. Das Telemediengesetz wurde am "
                        "14.05.2024 durch das Digitale-Dienste-Gesetz (DDG) abgelöst; die "
                        "Impressumspflicht steht jetzt in § 5 DDG. Die Angabe der Norm ist nicht "
                        "vorgeschrieben — wenn sie dasteht, sollte sie stimmen.",
                        s.url, _erstes(RE_TMG, s.text)))

    return b


def pruefe_datenschutz(s: Seite) -> list[Befund]:
    """Art. 13 DSGVO — die Informationspflichten."""
    b: list[Befund] = []

    # Art. 13 Abs. 1 lit. a: Name UND Kontaktdaten des Verantwortlichen.
    # Genau die Regel, an der layer8 seinen Build abbricht.
    nennt_verantwortlichen = s.enthaelt(r"Verantwortliche[rn]?\b", r"Verantwortlichkeit")
    hat_kontakt = bool(_hat_email(s) or RE_TELEFON.search(s.text) or RE_STRASSE.search(s.text))
    if nennt_verantwortlichen and hat_kontakt:
        b.append(Befund("D-VERANTWORTLICHER", Grad.OK, "Art. 13 Abs. 1 lit. a DSGVO",
                        "Verantwortlicher benannt, Kontaktdaten vorhanden.", s.url, _hat_email(s)))
    elif nennt_verantwortlichen and not hat_kontakt:
        b.append(Befund("D-VERANTWORTLICHER", Grad.FEHLER, "Art. 13 Abs. 1 lit. a DSGVO",
                        "Ein Verantwortlicher wird erwähnt, aber es sind keine Kontaktdaten "
                        "erkennbar. Art. 13 Abs. 1 lit. a DSGVO verlangt Name UND Kontaktdaten.",
                        s.url))
    else:
        b.append(Befund("D-VERANTWORTLICHER", Grad.FEHLER, "Art. 13 Abs. 1 lit. a DSGVO",
                        "Kein Verantwortlicher benannt. Art. 13 Abs. 1 lit. a DSGVO verlangt Name "
                        "und Kontaktdaten des Verantwortlichen.",
                        s.url))

    # Art. 13 Abs. 2 lit. b: die Betroffenenrechte.
    rechte = {
        "Auskunft": r"Auskunft(srecht)?|Recht auf Auskunft",
        "Berichtigung": r"Berichtigung",
        "Löschung": r"L[öo]schung|Recht auf Vergessenwerden",
        "Einschränkung": r"Einschr[äa]nkung der Verarbeitung",
        "Widerspruch": r"Widerspruch",
        "Datenübertragbarkeit": r"Daten[üu]bertragbarkeit",
    }
    fehlend = [name for name, m in rechte.items() if not s.enthaelt(m)]
    if not fehlend:
        b.append(Befund("D-BETROFFENENRECHTE", Grad.OK, "Art. 13 Abs. 2 lit. b DSGVO",
                        "Alle sechs Betroffenenrechte genannt.", s.url))
    elif len(fehlend) >= 4:
        b.append(Befund("D-BETROFFENENRECHTE", Grad.FEHLER, "Art. 13 Abs. 2 lit. b DSGVO",
                        f"Betroffenenrechte weitgehend nicht genannt (es fehlen: {', '.join(fehlend)}).",
                        s.url))
    else:
        b.append(Befund("D-BETROFFENENRECHTE", Grad.WARNUNG, "Art. 13 Abs. 2 lit. b DSGVO",
                        f"Nicht alle Betroffenenrechte genannt (es fehlen: {', '.join(fehlend)}).",
                        s.url))

    # Art. 13 Abs. 2 lit. d: Beschwerderecht bei einer Aufsichtsbehörde.
    if s.enthaelt(r"Beschwerde", r"Aufsichtsbeh[öo]rde"):
        b.append(Befund("D-BESCHWERDE", Grad.OK, "Art. 13 Abs. 2 lit. d DSGVO",
                        "Beschwerderecht bei einer Aufsichtsbehörde genannt.", s.url))
    else:
        b.append(Befund("D-BESCHWERDE", Grad.FEHLER, "Art. 13 Abs. 2 lit. d DSGVO",
                        "Kein Hinweis auf das Beschwerderecht bei einer Aufsichtsbehörde.", s.url))

    # Art. 13 Abs. 1 lit. c: Zwecke UND Rechtsgrundlage.
    if s.enthaelt(r"Rechtsgrundlage", r"Art(?:ikel)?\.?\s*6\s*(?:Abs|Absatz)"):
        b.append(Befund("D-RECHTSGRUNDLAGE", Grad.OK, "Art. 13 Abs. 1 lit. c DSGVO",
                        "Rechtsgrundlage der Verarbeitung genannt.", s.url))
    else:
        b.append(Befund("D-RECHTSGRUNDLAGE", Grad.WARNUNG, "Art. 13 Abs. 1 lit. c DSGVO",
                        "Keine Rechtsgrundlage erkennbar (Art. 13 Abs. 1 lit. c DSGVO verlangt "
                        "Zwecke und Rechtsgrundlage).",
                        s.url))

    # Art. 13 Abs. 2 lit. a: Speicherdauer oder deren Kriterien.
    if s.enthaelt(r"Speicherdauer", r"Dauer.{0,30}gespeichert", r"gespeichert.{0,40}Dauer", r"L[öo]schfrist", r"Aufbewahrungs(?:frist|dauer)"):
        b.append(Befund("D-SPEICHERDAUER", Grad.OK, "Art. 13 Abs. 2 lit. a DSGVO",
                        "Angabe zur Speicherdauer gefunden.", s.url))
    else:
        b.append(Befund("D-SPEICHERDAUER", Grad.WARNUNG, "Art. 13 Abs. 2 lit. a DSGVO",
                        "Keine Angabe zur Speicherdauer (oder zu den Kriterien für ihre Festlegung).",
                        s.url))

    return b


# ---------------------------------------------------------------------------
# Auffinden und Erreichbarkeit
# ---------------------------------------------------------------------------

RE_IMPRESSUM_LINK = re.compile(r"impressum|imprint|anbieterkennzeichnung|legal[-_\s]?notice", re.I)
RE_DATENSCHUTZ_LINK = re.compile(r"datenschutz|privacy|privacy[-_\s]?policy", re.I)


def _ist_treffer(lnk, muster: re.Pattern[str]) -> bool:
    return bool(muster.search(lnk.href) or muster.search(lnk.text))


def pruefe_erreichbarkeit(sm: Sammlung, muster: re.Pattern[str], was: str, regel: str) -> list[Befund]:
    """BGH I ZR 228/03: zwei Klicks sind zulässig, drei nicht mehr.

    Wir prüfen die strengere, praktisch relevante Variante: steht der Link
    auf JEDER Seite? Denn "ständig verfügbar" (§ 5 Abs. 1 DDG) heißt nicht
    "auf der Startseite verfügbar".
    """
    if not sm.seiten:
        return []

    ohne = [s.url for s in sm.seiten if not any(_ist_treffer(l, muster) for l in s.links)]
    # Die Zielseite selbst muss nicht auf sich selbst verlinken.
    ohne = [u for u in ohne if not muster.search(u)]

    if not ohne:
        return [Befund(regel, Grad.OK, "§ 5 Abs. 1 DDG; BGH I ZR 228/03",
                       f"{was}-Link ist von allen {len(sm.seiten)} geprüften Seiten aus direkt erreichbar.")]

    quote = len(ohne)
    beispiele = ", ".join(ohne[:3]) + (f" … (+{quote - 3} weitere)" if quote > 3 else "")
    return [Befund(regel, Grad.FEHLER, "§ 5 Abs. 1 DDG; BGH I ZR 228/03",
                   f"{was}-Link fehlt auf {quote} von {len(sm.seiten)} Seiten. § 5 Abs. 1 DDG verlangt "
                   f"„leicht erkennbar, unmittelbar erreichbar und ständig verfügbar“; der BGH "
                   f"(I ZR 228/03) lässt zwei Klicks genügen, nicht mehr.",
                   beleg=beispiele)]


def pruefe_alles(sm: Sammlung) -> list[Befund]:
    b: list[Befund] = []

    # Wenn nicht alles angesehen wurde, muss das im Bericht stehen — sonst
    # liest sich ein "auf allen Seiten erreichbar" wie eine Zusicherung, die
    # gar nicht geprüft wurde.
    if sm.gesamt > len(sm.seiten):
        b.append(Befund("STICHPROBE", Grad.HINWEIS, "—",
                        f"Nur {len(sm.seiten)} von {sm.gesamt} Seiten geprüft (Obergrenze). "
                        f"Aussagen zur Erreichbarkeit beziehen sich nur auf diese Stichprobe."))

    imp = sm.finde("impressum", "imprint", "anbieterkennzeichnung", "legal-notice")
    dat = sm.finde("datenschutz", "privacy")

    if imp:
        b.append(Befund("I-GEFUNDEN", Grad.OK, "§ 5 Abs. 1 DDG",
                        f"Impressum gefunden: {imp.url}", imp.url))
        b += pruefe_impressum(sm, imp)
        b += pruefe_erreichbarkeit(sm, RE_IMPRESSUM_LINK, "Impressum", "I-ERREICHBAR")
    else:
        b.append(Befund("I-GEFUNDEN", Grad.FEHLER, "§ 5 Abs. 1 DDG",
                        "Kein Impressum gefunden. Gesucht wurde nach Seiten und Links mit "
                        "„Impressum“, „Imprint“, „Anbieterkennzeichnung“ oder „/impressum“."))

    if dat:
        b.append(Befund("D-GEFUNDEN", Grad.OK, "Art. 13 DSGVO",
                        f"Datenschutzerklärung gefunden: {dat.url}", dat.url))
        b += pruefe_datenschutz(dat)
        b += pruefe_erreichbarkeit(sm, RE_DATENSCHUTZ_LINK, "Datenschutz", "D-ERREICHBAR")
    else:
        b.append(Befund("D-GEFUNDEN", Grad.FEHLER, "Art. 13 DSGVO",
                        "Keine Datenschutzerklärung gefunden."))

    return b
