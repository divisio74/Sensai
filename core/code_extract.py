
def extract_code(text):
    chunk = text.split("```")
    if len(chunk) == 1:
        return chunk[0].strip()
    return chunk[1].removeprefix("python").strip()
