import re


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\xa0", " ")

    cleaned_lines = []

    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line)
        line = line.strip()

        if line:
            cleaned_lines.append(line)

    # Rows ke darmiyan newline preserve rahegi
    return "\n".join(cleaned_lines)
