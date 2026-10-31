import json
import re
import hashlib
import secrets
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"

def load_users():
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))

def user_exists(email):
    return email in load_users()

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()

def profile_path(email):
    return DATA_DIR / "profiles" / f"{email}.md"

def register(email, password, persona, about):
    if not re.fullmatch(r"[\w.+@-]+", email):
        return "Invalid email: only letters, digits and . _ - + @ are allowed."
    if not password:
        return "Password cannot be empty."
    users = load_users()
    if email in users:
        return "An account already exists for this email."
    salt = secrets.token_hex(16)
    users[email] = {"salt": salt, "hash": hash_password(password, salt), "persona": persona}
    profile_path(email).parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")
    profile_path(email).write_text(f"# User profile\n\n## About me\n{about.strip()}\n\n## Preferences\n\n## Remembered facts\n", encoding="utf-8")
    return None

def login(email, password):
    user = load_users().get(email)
    if user is None or not secrets.compare_digest(user["hash"], hash_password(password, user["salt"])):
        return None
    return {"email": email, "persona": user["persona"]}
