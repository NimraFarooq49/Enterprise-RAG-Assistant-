import os
import re
import pdfplumber


def load_document(file_path: str):
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        return extract_pdf(file_path)

    if extension == ".txt":
        return extract_text(file_path)

    if extension == ".md":
        return extract_markdown(file_path)

    raise ValueError("Unsupported file type")


def clean_table_cell(value) -> str:
    if value is None:
        return ""

    value = str(value)

    value = value.replace("\r\n", " ")
    value = value.replace("\n", " ")
    value = value.replace("\r", " ")
    value = value.replace("\xa0", " ")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def table_to_text(table) -> str:
    if not table:
        return ""

    cleaned_rows = []

    for row in table:
        cleaned_row = [clean_table_cell(cell) for cell in row]

        if any(cleaned_row):
            cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return ""
    headers = cleaned_rows[0]

    headers = [
        header if header else f"Column {index + 1}"
        for index, header in enumerate(headers)
    ]

    output_rows = []

    for row in cleaned_rows[1:]:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))

        if len(row) > len(headers):
            row = row[: len(headers)]

        row_values = []

        for header, value in zip(headers, row):
            if value:
                row_values.append(f"{header}: {value}")

        if row_values:
            output_rows.append("; ".join(row_values))

    if not output_rows and cleaned_rows:
        first_row = cleaned_rows[0]

        output_rows.append(
            "; ".join(
                f"Column {index + 1}: {value}"
                for index, value in enumerate(first_row)
                if value
            )
        )

    return "\n".join(output_rows)


def extract_pdf(file_path: str):
    pages = []

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):

            # Normal PDF text extract
            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=3,
            )

            if page_text and page_text.strip():
                pages.append(
                    {
                        "page_number": page_number,
                        "content_type": "text",
                        "text": page_text.strip(),
                    }
                )
            tables = page.extract_tables()

            for table in tables:
                table_text = table_to_text(table)

                if table_text:
                    pages.append(
                        {
                            "page_number": page_number,
                            "content_type": "text",
                            "text": table_text,
                        }
                    )

    return pages


def extract_text(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    page_size = 2000
    pages = []

    for start in range(0, len(text), page_size):
        page_number = (start // page_size) + 1
        page_text = text[start : start + page_size].strip()

        if page_text:
            pages.append(
                {
                    "page_number": page_number,
                    "content_type": "text",
                    "text": page_text,
                }
            )

    return pages


def extract_markdown(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    page_size = 2000
    pages = []

    for start in range(0, len(text), page_size):
        page_number = (start // page_size) + 1
        page_text = text[start : start + page_size].strip()

        if page_text:
            pages.append(
                {
                    "page_number": page_number,
                    "content_type": "text",
                    "text": page_text,
                }
            )

    return pages
