# impressum-check

**Prüft, ob die Pflichtangaben DA sind. Nicht, ob sie STIMMEN.**

Das ist keine Nebenbemerkung, das ist die Bedienungsanleitung. Eine erfundene
Anschrift besteht jede Prüfung dieses Werkzeugs. Ein Geschäftsführer, der nicht
existiert, besteht sie. Eine USt-IdNr. mit neun Ziffern, die niemandem gehört,
besteht sie.

Das Werkzeug prüft **Vollständigkeit, nicht Wahrheit** — es zählt Pflichtfelder
ab. Wer daraus „meine Seite ist rechtssicher“ liest, hat sich ein grünes Häkchen
gekauft und sonst nichts. Genau das ist die Sorte Werkzeug, die falsche
Sicherheit gibt, und deshalb steht dieser Absatz vor allem anderen.

**Es ist keine Rechtsberatung.** Ob Ihre Seite überhaupt impressumspflichtig ist,
ob Ihr Beruf reglementiert ist, ob Sie eine Aufsichtsbehörde nennen müssen — das
sind Rechtsfragen. Dieses Programm beantwortet sie nicht. Es findet fehlende
Felder, und das ist alles.

## Wozu dann?

Weil eine fehlende Pflichtangabe **abmahnfähig** ist und weil sie sich
**maschinell finden lässt**. Die Angaben nach § 5 DDG sind eine Aufzählung, keine
Meinungsfrage: Anschrift, E-Mail, Register, Vertreter. Fehlt eines, fehlt es
nachweisbar — und das kann eine CI feststellen, bevor die Seite live geht, statt
eines Anwalts danach.

```console
$ impressum-check beispiel
✗ FEHLER   I-POSTFACH           Nur ein Postfach angegeben.
✗ FEHLER   I-VERTRETER          „GmbH“ genannt, aber kein Vertretungsberechtigter.
✗ FEHLER   I-REGISTER           „GmbH“ genannt, aber es fehlt: Registergericht, Registernummer (HRB/HRA/…).
✗ FEHLER   I-USTID              USt-IdNr. „DE1234567“ hat 7 Ziffern.
✗ FEHLER   D-VERANTWORTLICHER   Kein Verantwortlicher benannt.
```

Fünf Fehler, und keiner davon ist ein Tippfehler: das Postfach ist keine
ladungsfähige Anschrift, die GmbH nennt weder Geschäftsführer noch Handelsregister,
die Umsatzsteuer-ID hat zwei Ziffern zu wenig, und die Datenschutzerklärung sagt
nicht, wer verantwortlich ist. Jeder einzelne davon steht im Gesetz.

## Es heißt DDG, nicht TMG

Das Telemediengesetz wurde am **14.05.2024 durch das Digitale-Dienste-Gesetz
(DDG)** abgelöst. Die Impressumspflicht steht seither in
[§ 5 DDG](https://www.gesetze-im-internet.de/ddg/__5.html), inhaltlich unverändert.

Sehr viele Impressen zitieren noch „Angaben gemäß § 5 TMG“. Das ist für sich
genommen **kein Fehler** — die Norm muss gar nicht genannt werden. Aber es ist ein
zuverlässiger Hinweis darauf, dass die Seite seit Mai 2024 niemand mehr angesehen
hat, und deshalb meldet das Werkzeug es als Warnung, nicht als Fehler. Wer ein
Gesetz zitiert, sollte das richtige zitieren.

## Was geprüft wird

**Impressum — § 5 Abs. 1 DDG:**

| Prüfung | Norm | was auffällt |
| --- | --- | --- |
| `I-ANSCHRIFT` | Nr. 1 | Straße + Hausnummer + PLZ + Ort |
| `I-POSTFACH` | Nr. 1 | ein Postfach ist **keine** ladungsfähige Anschrift |
| `I-VERTRETER` | Nr. 1 | bei GmbH/UG/AG: Geschäftsführer, Vorstand |
| `I-EMAIL` | Nr. 2 | E-Mail-Adresse, auch als `mailto:` |
| `I-ZWEITER-WEG` | Nr. 2 | Telefon **oder** Kontaktformular |
| `I-REGISTER` | Nr. 4 | bei GmbH/UG/AG: Registergericht + HRB/HRA |
| `I-USTID` | Nr. 6, § 27a UStG | Format `DE` + 9 Ziffern, **falls angegeben** |
| `I-ERREICHBAR` | § 5 Abs. 1, BGH I ZR 228/03 | von **jeder** Seite verlinkt? |
| `I-TMG-VERALTET` | — | zitiert das abgelöste Gesetz |

**Datenschutzerklärung — Art. 13 DSGVO:**

| Prüfung | Norm |
| --- | --- |
| `D-VERANTWORTLICHER` | Abs. 1 lit. a — Name **und** Kontaktdaten |
| `D-RECHTSGRUNDLAGE` | Abs. 1 lit. c — Zwecke und Rechtsgrundlage |
| `D-SPEICHERDAUER` | Abs. 2 lit. a |
| `D-BETROFFENENRECHTE` | Abs. 2 lit. b — alle sechs |
| `D-BESCHWERDE` | Abs. 2 lit. d — Beschwerderecht bei einer Aufsichtsbehörde |

Die **Telefonnummer ist nicht zwingend.** Der EuGH hat das 2008 entschieden
([C-298/07](https://curia.europa.eu/juris/liste.jsf?num=C-298/07)): neben der
E-Mail braucht es einen zweiten Weg zur „unmittelbaren und effizienten
Kommunikation“ — ein Kontaktformular genügt. Ein Prüfer, der eine Telefonnummer
verlangt, erfindet eine Pflicht, und dafür gibt es einen Test.

Die **Zwei-Klick-Regel** stammt vom BGH ([I ZR 228/03](https://dejure.org/dienste/vernetzung/rechtsprechung?Gericht=BGH&Datum=2006-07-20&Aktenzeichen=I+ZR+228%2F03),
Urteil vom 20.07.2006): ein über zwei Links erreichbares Impressum ist „leicht
erkennbar und unmittelbar erreichbar“. Drei sind es nicht mehr. Geprüft wird die
praktisch strengere Frage: steht der Link auf **jeder** Seite? „Ständig verfügbar“
(§ 5 Abs. 1 DDG) heißt nicht „auf der Startseite verfügbar“.

## Für die CI

Der Punkt des Werkzeugs ist, dass es **vor** dem Deploy läuft. Eine Prüfung, die
erst die fertige Website abfragt, prüft eine Seite, die bereits online ist — das
ist keine CI, das ist eine Obduktion.

Deshalb frisst es einen Build-Ordner:

<!-- readme-check: skip=illustration -->
```console
$ impressum-check dist/            # der CI-Fall
$ impressum-check https://…        # eine fertige Seite (folgt Links, 2 Klicks tief)
$ impressum-check impressum.html   # eine einzelne Datei
```

Exit `1`, sobald eine Pflichtangabe fehlt. Warnungen brechen den Build nicht —
es sei denn, Sie wollen es:

<!-- readme-check: skip=illustration -->
```console
$ impressum-check dist/ --streng          # Warnungen zählen als Fehler
$ impressum-check dist/ --kein-exit-code  # nur berichten, nie brechen
$ impressum-check dist/ --json            # maschinenlesbar
$ impressum-check dist/ -q                # nur zeigen, was nicht stimmt
```

Der Vorläufer dieses Werkzeugs steckt in `layer8`: dort bricht der Astro-Build ab,
wenn in der Datenschutzerklärung kein Verantwortlicher steht (`src/pages/datenschutz.astro`).
Das ist genau die Regel `D-VERANTWORTLICHER`, nur für eine Seite fest verdrahtet.
Hier ist sie für jede Seite.

## Was es nicht kann

Über die Wahrheitsfrage hinaus, die schon oben steht:

- **Es liest kein JavaScript.** Ein Impressum, das erst im Browser
  zusammengesetzt wird, ist für dieses Werkzeug nicht vorhanden. (Für den Googlebot
  übrigens auch nur mit Glück.)
- **Es kennt Ihren Beruf nicht.** Ob Sie Kammer, Berufsbezeichnung oder
  Aufsichtsbehörde nennen müssen (§ 5 Abs. 1 Nr. 3 und Nr. 5 DDG), hängt davon ab,
  wer Sie sind. Das Werkzeug prüft diese Felder **nicht** und tut auch nicht so.
- **Es prüft [§ 18 Abs. 2 MStV](https://www.gesetze-bayern.de/Content/Document/MStV-18)
  nicht.** Journalistisch-redaktionelle Angebote brauchen zusätzlich einen
  Verantwortlichen — eine **natürliche** Person, mit Name und Anschrift. Ob Ihre
  Seite ein solches Angebot ist, ist eine Rechtsfrage, und sie zu beantworten ist
  nicht Sache eines Regex. Ein Blog mit redaktionellen Beiträgen kann darunter
  fallen.
- **Es erkennt Anschriften heuristisch.** Deutsche Straßennamen, deutsche
  Postleitzahlen. Eine österreichische oder schweizerische Adresse erkennt es nicht
  zuverlässig — es ist für den deutschen Rechtsraum gebaut.
- **Es sagt Ihnen nicht, ob Sie impressumspflichtig sind.** § 5 DDG gilt für
  „geschäftsmäßig … angebotene digitale Dienste“. Was das für Ihre Seite bedeutet,
  entscheidet kein Programm.

Falsch-negative sind hier die teuren: Wenn es schweigt, heißt das *nicht*, dass
alles in Ordnung ist. Es heißt, dass die Felder, die es kennt, gefüllt sind.

## Geprüft

```console
$ python -m pytest -q
54 passed
```

Jeder Fehlerfall hat einen Test — und **jeder Fehlerfall hat einen Gegentest**:
das Postfach neben einer echten Hausanschrift (kein Mangel), der Einzelunternehmer
ohne Handelsregister (keine Pflicht), das Kontaktformular statt der Telefonnummer
(nach EuGH zulässig), die USt-IdNr. mit Leerzeichen (dieselbe Nummer), die fehlende
USt-IdNr. (nur „sofern vorhanden“ Pflicht).

Das ist der schwierigere Teil. Fehler zu finden ist leicht, wenn man bereit ist,
das Richtige mitanzuschreien.

Das Werkzeug ist <!-- readme-check: 804 = cat impressumcheck/*.py | wc -l --> 804
Zeilen Python, und diese Zahl wird von dem Code geprüft, den sie zählt.

## Installation

<!-- readme-check: skip=would-install -->
```console
$ pip install impressum-check
```

Python 3.10+, **keine Abhängigkeiten**. Das HTML-Parsing macht `html.parser` aus
der Standardbibliothek. Für „finde den sichtbaren Text und die Links“ hätte
`beautifulsoup4` nichts hinzugefügt, was eine Abhängigkeit wert wäre — und ein
Werkzeug, das in fremde CI-Pipelines soll, sollte so wenig wie möglich mitbringen.

## Lizenz

MIT
