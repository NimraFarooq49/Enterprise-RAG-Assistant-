def chunk_text(
    pages,
    document_id: int,
    file_name: str,
    chunk_size: int = 1000,
    overlap: int = 150,
):
    chunks = []
    chunk_number = 1

    def add_chunk(text, page_number, content_type):
        nonlocal chunk_number

        text = text.strip()

        if not text:
            return

        chunks.append(
            {
                "document_id": document_id,
                "file_name": file_name,
                "chunk_number": chunk_number,
                "page_number": page_number,
                "content_type": content_type,
                "text": text,
            }
        )

        chunk_number += 1

    for page in pages:
        text = page.get("text", "").strip()
        page_number = page.get("page_number")
        content_type = page.get("content_type", "text")

        if not text:
            continue

        if content_type == "table":
            rows = [row.strip() for row in text.splitlines() if row.strip()]

            current_rows = []
            current_length = 0

            for row in rows:
                row_length = len(row) + 1

                if current_rows and current_length + row_length > chunk_size:
                    add_chunk(
                        "\n".join(current_rows),
                        page_number,
                        "text",
                    )

                    current_rows = []
                    current_length = 0

                current_rows.append(row)
                current_length += row_length

            if current_rows:
                add_chunk(
                    "\n".join(current_rows),
                    page_number,
                    "text",
                )

            continue

        # Normal text chunks
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            if end < len(text):
                last_space = text.rfind(" ", start, end)

                if last_space > start:
                    end = last_space

            chunk = text[start:end].strip()

            if chunk:
                add_chunk(
                    chunk,
                    page_number,
                    "text",
                )

            if end >= len(text):
                break

            next_start = max(start + 1, end - overlap)

            while next_start < len(text) and text[next_start].isspace():
                next_start += 1

            if next_start <= start:
                next_start = end

            start = next_start

    return chunks
