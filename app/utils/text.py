# app/utils/text.py

import pandas as pd
import unicodedata

def _norm(s):
    """Normaliza strings: None->'', quita acentos, strip, lower, colapsa espacios."""
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.strip().lower()
    s = " ".join(s.split())
    return s