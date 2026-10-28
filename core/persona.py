from datetime import date
from pathlib import Path

path = Path(__file__).resolve()
racine = path.parent.parent
PERSONAS_DIR = racine / "persona" / "personas"

def load_persona(persona_id):
    chemin = PERSONAS_DIR / f"{persona_id}.md"
    texte = chemin.read_text(encoding="utf-8")
    return texte

def build_system_prompt(persona_text):
    return {"role": "system", "content": f"{persona_text}\n\nToday's date is {date.today().isoformat()}."}