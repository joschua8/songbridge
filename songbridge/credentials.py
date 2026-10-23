"""Gespeichertes ChurchTools-Passwort – bleibt über Programm- und Computerneustarts erhalten.

Bevorzugt im Schlüsselbund des Betriebssystems (macOS-Schlüsselbund, Windows-Anmeldeinformationsverwaltung,
unter Linux z. B. GNOME-Schlüsselbund) über das Paket `keyring`. Gibt es dort keinen nutzbaren Speicher,
landet das Passwort in `credentials.json` im Datenordner (nur für den eigenen Benutzer lesbar, unverschlüsselt).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from songbridge.paths import DATA_DIR

SERVICE = "SongBridge"
FILE_PATH = Path(os.environ.get("SONGBRIDGE_CREDENTIALS", DATA_DIR / "credentials.json"))

try:
    import keyring
    from keyring.errors import KeyringError
except ImportError:  # pragma: no cover - keyring fehlt nur bei unvollständiger Installation
    keyring = None

    class KeyringError(Exception):
        pass


def _account(url: str, user: str) -> str:
    return f"{user.strip()}@{url.strip().rstrip('/')}"


def _keyring_usable() -> bool:
    """False, wenn kein echter Schlüsselbund da ist (z. B. Linux ohne Secret Service)."""
    if keyring is None:
        return False
    try:
        # Ersatz-Backends ohne Speicher (fail/null, leerer Chainer) haben Priorität <= 0
        return keyring.get_keyring().priority > 0
    except Exception:  # noqa: BLE001 - Backend-Suche kann je nach System beliebig scheitern
        return False


def _read_file() -> dict:
    try:
        data = json.loads(FILE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_file(data: dict) -> None:
    if not data:
        FILE_PATH.unlink(missing_ok=True)
        return
    FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE_PATH.with_suffix(".tmp")
    # Datei gleich mit 0600 anlegen, damit das Passwort nie kurz für andere lesbar ist
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    tmp.replace(FILE_PATH)


def save_password(url: str, user: str, password: str) -> str:
    """Speichert das Passwort; -> "keyring" oder "file" (wo es gelandet ist)."""
    account = _account(url, user)
    if _keyring_usable():
        try:
            keyring.set_password(SERVICE, account, password)
            _drop_from_file(account)  # alte Kopie aus der Datei entfernen
            return "keyring"
        except (KeyringError, OSError, RuntimeError):
            pass
    data = _read_file()
    data[account] = password
    _write_file(data)
    return "file"


def load_password(url: str, user: str) -> str:
    if not url or not user:
        return ""
    account = _account(url, user)
    if _keyring_usable():
        try:
            pw = keyring.get_password(SERVICE, account)
            if pw:
                return pw
        except (KeyringError, OSError, RuntimeError):
            pass
    value = _read_file().get(account)
    return value if isinstance(value, str) else ""


def delete_password(url: str, user: str) -> None:
    if not url or not user:
        return
    account = _account(url, user)
    if _keyring_usable():
        try:
            keyring.delete_password(SERVICE, account)
        except (KeyringError, OSError, RuntimeError):
            pass  # war nicht gespeichert
    _drop_from_file(account)


def _drop_from_file(account: str) -> None:
    data = _read_file()
    if account in data:
        del data[account]
        _write_file(data)
