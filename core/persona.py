from datetime import date
from pathlib import Path

path = Path(__file__).resolve()
racine = path.parent.parent
PERSONAS_DIR = racine / "persona" / "personas"
USER_FILE = racine / "persona" / "user.md"
USER_TEMPLATE = racine / "persona" / "user.example.md"

def load_persona(persona_id):
    real_path = PERSONAS_DIR / f"{persona_id}.md"
    text = real_path.read_text(encoding="utf-8")
    return text

def list_personas():
    return sorted(path.stem for path in PERSONAS_DIR.glob("*.md"))

def get_persona_name(persona_id):
    text = load_persona(persona_id)
    for line in text.splitlines():
        if line.startswith("# "):
            name = line[2:].strip()
            return name
    return "Assistant"

def load_user_profile(profile_file=USER_FILE):
    if not profile_file.exists():
        return ""
    return profile_file.read_text(encoding="utf-8")

def remember(fact, profile_file=USER_FILE):
    if not profile_file.exists() and USER_TEMPLATE.exists():
        profile_file.write_text(USER_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    with open(profile_file, "a", encoding="utf-8") as f:
        f.write(f"- {fact.strip()}\n")

def build_system_prompt(persona_text, user_profile=""):
    content = f"{persona_text}\n\nToday's date is {date.today().isoformat()}."
    if user_profile:
        content += "\n\nAbout the user you are talking to. Their preferences below override your default behavior:\n" + user_profile
    return {"role": "system", "content": content}
