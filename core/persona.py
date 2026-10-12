from pathlib import Path

path = Path(__file__).resolve()
racine = path.parent.parent
PERSONAS_DIR = racine / "persona" / "personas"

def load_persona(persona_id):
    real_path = PERSONAS_DIR / f"{persona_id}.md"
    text = real_path.read_text(encoding="utf-8")
    return text

def get_persona_name(persona_id):
    text = load_persona(persona_id)
    for line in text.splitlines():
        if line.startswith("# "):
            name = line[2:].strip()
            return name
    return "Assistant"

def build_system_prompt(persona_text):
    return {"role": "system", "content": persona_text}