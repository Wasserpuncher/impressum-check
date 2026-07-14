"""impressum-check — Pflichtangaben nach § 5 DDG und Art. 13 DSGVO prüfen.

Prüft, ob die Angaben DA sind. Nicht, ob sie STIMMEN. Keine Rechtsberatung.
"""

from .parse import Seite, parse
from .quellen import Sammlung, laden
from .regeln import Befund, Grad, pruefe_alles

__version__ = "0.1.0"
__all__ = ["Befund", "Grad", "Sammlung", "Seite", "laden", "parse", "pruefe_alles"]
