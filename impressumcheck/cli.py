"""Die Kommandozeile."""

from __future__ import annotations

import argparse
import json
import sys

from .regeln import Befund, Grad, pruefe_alles
from .quellen import laden

SYMBOL = {Grad.OK: "✓", Grad.FEHLER: "✗", Grad.WARNUNG: "!", Grad.HINWEIS: "·"}
FARBE = {Grad.OK: "\033[32m", Grad.FEHLER: "\033[31m", Grad.WARNUNG: "\033[33m", Grad.HINWEIS: "\033[90m"}
AUS = "\033[0m"


def _text_bericht(befunde: list[Befund], herkunft: str, farbig: bool, ruhig: bool) -> str:
    z: list[str] = [f"impressum-check  {herkunft}", ""]

    def f(g: Grad, s: str) -> str:
        return f"{FARBE[g]}{s}{AUS}" if farbig else s

    for b in befunde:
        if ruhig and b.grad is Grad.OK:
            continue
        z.append(f"{f(b.grad, SYMBOL[b.grad])} {f(b.grad, b.grad.value):8} {b.regel:20} {b.text}")
        if b.grad is not Grad.OK:
            z.append(f"           └─ {b.norm}")
        if b.beleg:
            z.append(f"           └─ gefunden: {b.beleg}")

    fehler = sum(1 for b in befunde if b.grad is Grad.FEHLER)
    warn = sum(1 for b in befunde if b.grad is Grad.WARNUNG)
    ok = sum(1 for b in befunde if b.grad is Grad.OK)

    z.append("")
    if fehler:
        z.append(f(Grad.FEHLER, f"{fehler} Pflichtangabe(n) fehlen, {warn} Warnung(en), {ok} in Ordnung"))
    elif warn:
        z.append(f(Grad.WARNUNG, f"Keine fehlende Pflichtangabe, {warn} Warnung(en), {ok} in Ordnung"))
    else:
        z.append(f(Grad.OK, f"Alle {ok} Prüfungen bestanden"))

    # Dieser Satz steht bewusst in JEDER Ausgabe, nicht nur im README.
    # Ein grünes Häkchen, das man aus dem Kontext reißen kann, ist gefährlicher
    # als ein rotes Kreuz.
    z.append("")
    z.append("Geprüft wurde, ob die Angaben DA sind — nicht, ob sie STIMMEN.")
    z.append("Das ist keine Rechtsberatung.")
    return "\n".join(z)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="impressum-check",
        description="Prüft, ob eine deutsche Website die Pflichtangaben nach § 5 DDG "
                    "und Art. 13 DSGVO enthält. Keine Rechtsberatung.",
        epilog="Das Werkzeug prüft Vollständigkeit, nicht Wahrheit: eine erfundene "
               "Anschrift besteht jede Prüfung.",
    )
    p.add_argument("ziel", help="URL, HTML-Datei oder Ordner (z. B. dist/)")
    p.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe")
    p.add_argument("--streng", action="store_true", help="Warnungen zählen als Fehler")
    p.add_argument("--ruhig", "-q", action="store_true", help="Nur zeigen, was nicht in Ordnung ist")
    p.add_argument("--timeout", type=float, default=10.0, help="Timeout je Abruf in Sekunden (Standard: 10)")
    p.add_argument("--kein-exit-code", action="store_true",
                   help="Immer 0 zurückgeben (nur berichten, CI nicht brechen)")
    a = p.parse_args(argv)

    try:
        sm = laden(a.ziel, timeout=a.timeout)
    except (FileNotFoundError, ValueError) as e:
        print(f"impressum-check: {e}", file=sys.stderr)
        return 2

    if not sm.seiten:
        print(f"impressum-check: keine HTML-Seiten gefunden in {a.ziel}", file=sys.stderr)
        return 2

    befunde = pruefe_alles(sm)

    if a.json:
        print(json.dumps({
            "herkunft": sm.herkunft,
            "geprüfte_seiten": len(sm.seiten),
            "befunde": [
                {"regel": b.regel, "grad": b.grad.value, "norm": b.norm,
                 "text": b.text, "seite": b.seite, "beleg": b.beleg}
                for b in befunde
            ],
            "hinweis": "Geprüft wurde, ob die Angaben da sind, nicht ob sie stimmen. "
                       "Keine Rechtsberatung.",
        }, ensure_ascii=False, indent=2))
    else:
        farbig = sys.stdout.isatty()
        print(_text_bericht(befunde, sm.herkunft, farbig, a.ruhig))

    if a.kein_exit_code:
        return 0
    schlimm = [b for b in befunde
               if b.grad is Grad.FEHLER or (a.streng and b.grad is Grad.WARNUNG)]
    return 1 if schlimm else 0


if __name__ == "__main__":
    sys.exit(main())
