import os
from pypdf import PdfReader


def load_document(file_path: str):

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        return extract_pdf(file_path)

    elif extension in [".txt", ".md"]:
        return extract_text(file_path)

    else:
        raise ValueError("Unsupported file type")


def extract_pdf(file_path: str):
    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"
    return text


def extract_text(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()
