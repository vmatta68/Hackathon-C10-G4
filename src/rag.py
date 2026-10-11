from __future__ import annotations

from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _load_chunks(runbook_dir: str | Path) -> list[dict[str, str]]:
    root = Path(runbook_dir)
    root.mkdir(parents=True, exist_ok=True)
    chunks: list[dict[str, str]] = []

    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        if not path.is_file():
            continue

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        paragraphs = [
            p.strip()
            for p in text.split("\n\n")
            if p.strip()
        ]

        pending_headings = []
        chunk_id = 0

        for paragraph in paragraphs:
            lines = paragraph.splitlines()

            # Keep headings with the content that follows them.
            is_heading_only = all(
                line.strip().startswith("#")
                for line in lines
            )

            if is_heading_only:
                pending_headings.append(paragraph)
                continue

            combined = "\n".join(
                pending_headings + [paragraph]
            ).strip()
            pending_headings = []

            for start in range(0, len(combined), 1200):
                chunk = combined[start:start + 1200].strip()

                if chunk:
                    chunks.append({
                        "source": path.name,
                        "chunk_id": str(chunk_id),
                        "text": chunk,
                    })
                    chunk_id += 1

    return chunks


def retrieve_runbook_context(query: str, runbook_dir: str | Path, top_k: int = 4) -> list[dict[str, str]]:
    chunks = _load_chunks(runbook_dir)
    if not chunks or not query.strip():
        return []
    corpus = [c["text"] for c in chunks]
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=12000)
        matrix = vectorizer.fit_transform(corpus + [query])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    except ValueError:
        return []
    ranked = scores.argsort()[::-1][:max(1, top_k)]
    return [
        {**chunks[int(i)], "score": f"{scores[int(i)]:.3f}"}
        for i in ranked
        if scores[int(i)] > 0
    ]
