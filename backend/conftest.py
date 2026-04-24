"""
Root conftest pour pytest — charge /app/backend/.env AVANT l'import des modules
des tests. Sans ça, `deps.py` plante au top-level sur `os.environ["MONGO_URL"]`.

Ce fichier est automatiquement découvert par pytest (convention).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

# Pour les tests d'intégration HTTP (iteration*.py) qui lisent REACT_APP_BACKEND_URL,
# on fournit un fallback raisonnable pointant vers l'API locale.
os.environ.setdefault("REACT_APP_BACKEND_URL", "http://localhost:8001")
