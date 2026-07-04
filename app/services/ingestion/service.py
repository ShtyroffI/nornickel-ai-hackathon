"""Импорт и нормализация данных: статьи, отчёты, патенты, протоколы."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class IngestedDocument:
    doc_id: str
    source_path: str
    language: str
    text: str


class IngestionService:
    SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf", ".docx", ".html"}

    def load(self, path: str | Path) -> IngestedDocument:
        p = Path(path)
        if p.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            raise ValueError(f"Unsupported file type: {p.suffix}")
        text = self._read(p)
        return IngestedDocument(
            doc_id=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
            source_path=str(p),
            language=self._detect_language(text),
            text=text,
        )

    def _read(self, p: Path) -> str:
        from app.utils.file_parsers import parse_file
        
        # Use our robust file parser which handles PDF, DOCX, TXT correctly
        text = parse_file(p)
        if not text:
            # Fallback to direct read if parser fails or returns empty
            return p.read_text(encoding="utf-8", errors="ignore")
        return text

    def _detect_language(self, text: str) -> str:
        cyrillic = sum(1 for c in text if "Ѐ" <= c <= "ӿ")
        return "ru" if cyrillic > len(text) * 0.05 else "en"
