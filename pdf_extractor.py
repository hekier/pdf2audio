"""
PDF text extraction module with quality heuristics and fallback support
"""

import re
import random
from pathlib import Path
from typing import Tuple, List, Dict, Optional
import logging

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from config import (
    BLANK_PAGE_CHAR_THRESHOLD,
    CHAR_DROP_THRESHOLD,
    MIN_PAGES_FOR_HEURISTICS,
    ABBREVIATIONS,
    PARAGRAPH_BREAK_MARKER,
)

logger = logging.getLogger(__name__)


class ExtractionConfidenceWarning(Exception):
    """Raised when extraction confidence is low"""
    pass


class PDFExtractor:
    """Extract and preprocess text from PDF documents"""

    def __init__(self, pdf_path: str, engine: str = "pymupdf"):
        """
        Initialize PDF extractor

        Args:
            pdf_path: Path to PDF file
            engine: Extraction engine ('pymupdf' or 'pdfplumber')
        """
        self.pdf_path = Path(pdf_path)
        self.engine = engine.lower()

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if self.engine == "pymupdf" and not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF is not installed")

        if self.engine == "pdfplumber" and not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber is not installed")

        self.page_count = self._get_page_count()
        self.page_texts: List[str] = []
        self.confidence_data: Dict = {}

    def _get_page_count(self) -> int:
        """Get total number of pages in PDF"""
        if self.engine == "pymupdf":
            doc = fitz.open(self.pdf_path)
            count = len(doc)
            doc.close()
            return count
        else:  # pdfplumber
            with pdfplumber.open(self.pdf_path) as pdf:
                return len(pdf.pages)

    def extract_page(self, page_num: int) -> str:
        """
        Extract text from a specific page

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Extracted text from the page
        """
        if self.engine == "pymupdf":
            return self._extract_page_pymupdf(page_num)
        else:
            return self._extract_page_pdfplumber(page_num)

    def _extract_page_pymupdf(self, page_num: int) -> str:
        """Extract page using PyMuPDF"""
        doc = fitz.open(self.pdf_path)
        page = doc[page_num]
        text = page.get_text()
        doc.close()
        return text

    def _extract_page_pdfplumber(self, page_num: int) -> str:
        """Extract page using pdfplumber"""
        with pdfplumber.open(self.pdf_path) as pdf:
            page = pdf.pages[page_num]
            text = page.extract_text() or ""
        return text

    def extract_random_page(self) -> Tuple[int, str]:
        """
        Extract a random page for testing

        Returns:
            Tuple of (page_number, extracted_text)
        """
        page_num = random.randint(0, self.page_count - 1)
        text = self.extract_page(page_num)
        logger.info(f"Extracted random page {page_num + 1} of {self.page_count}")
        return page_num, text

    def extract_all(self) -> str:
        """
        Extract all text from PDF with quality heuristics

        Returns:
            Complete extracted and cleaned text

        Raises:
            ExtractionConfidenceWarning: If extraction quality is suspicious
        """
        logger.info(f"Extracting text from {self.page_count} pages using {self.engine}")

        self.page_texts = []
        char_counts = []

        for page_num in range(self.page_count):
            text = self.extract_page(page_num)
            self.page_texts.append(text)
            char_counts.append(len(text.strip()))

        # Run confidence heuristics
        if self.page_count >= MIN_PAGES_FOR_HEURISTICS:
            self._check_extraction_confidence(char_counts)

        # Combine pages with paragraph markers
        full_text = PARAGRAPH_BREAK_MARKER.join(self.page_texts)

        # Preprocess text
        cleaned_text = self.preprocess_text(full_text)

        logger.info(f"Extracted {len(cleaned_text)} characters total")
        return cleaned_text

    def _check_extraction_confidence(self, char_counts: List[int]):
        """
        Check extraction quality using heuristics

        Args:
            char_counts: List of character counts per page

        Raises:
            ExtractionConfidenceWarning: If quality issues detected
        """
        # Check for blank pages
        blank_pages = sum(1 for count in char_counts if count < BLANK_PAGE_CHAR_THRESHOLD)
        blank_ratio = blank_pages / len(char_counts)

        if blank_ratio > 0.3:  # More than 30% blank pages
            warning = f"High number of blank pages detected ({blank_pages}/{len(char_counts)}). " \
                     f"PDF may be scanned or have extraction issues."
            logger.warning(warning)
            self.confidence_data['blank_pages_warning'] = warning

        # Check for character count drops
        non_blank_counts = [c for c in char_counts if c >= BLANK_PAGE_CHAR_THRESHOLD]
        if non_blank_counts:
            avg_chars = sum(non_blank_counts) / len(non_blank_counts)

            for i, count in enumerate(char_counts):
                if count > 0 and count < avg_chars * CHAR_DROP_THRESHOLD:
                    warning = f"Page {i + 1} has unusually low character count ({count} vs avg {int(avg_chars)})"
                    logger.warning(warning)
                    if 'char_drop_warnings' not in self.confidence_data:
                        self.confidence_data['char_drop_warnings'] = []
                    self.confidence_data['char_drop_warnings'].append((i + 1, count, int(avg_chars)))

        # Check for no text extracted
        total_chars = sum(char_counts)
        if total_chars < 100:
            raise ExtractionConfidenceWarning(
                "Very little text extracted. PDF may be scanned or image-based. "
                "Try using OCR preprocessing tools."
            )

    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Clean and preprocess extracted text

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text ready for TTS
        """
        # Remove excessive whitespace while preserving paragraph breaks
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n +', '\n', text)  # Space after newline
        text = re.sub(r' +\n', '\n', text)  # Space before newline

        # Handle hyphenation at line breaks
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)  # word-\nword -> wordword

        # Normalize paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)  # More than 2 newlines to 2

        # Expand abbreviations for more natural speech
        for abbr, expansion in ABBREVIATIONS.items():
            # Word boundary matching to avoid partial replacements
            text = re.sub(r'\b' + re.escape(abbr) + r'\b', expansion, text)

        # Clean up any remaining issues
        text = text.strip()

        return text

    def get_confidence_report(self) -> Optional[str]:
        """
        Get a human-readable confidence report

        Returns:
            Report string or None if no issues
        """
        if not self.confidence_data:
            return None

        report_lines = ["Extraction Quality Warnings:"]

        if 'blank_pages_warning' in self.confidence_data:
            report_lines.append(f"- {self.confidence_data['blank_pages_warning']}")

        if 'char_drop_warnings' in self.confidence_data:
            report_lines.append("- Character count anomalies detected:")
            for page_num, count, avg in self.confidence_data['char_drop_warnings'][:5]:
                report_lines.append(f"  * Page {page_num}: {count} chars (avg: {avg})")

            if len(self.confidence_data['char_drop_warnings']) > 5:
                remaining = len(self.confidence_data['char_drop_warnings']) - 5
                report_lines.append(f"  * ...and {remaining} more")

        report_lines.append("\nConsider using --layout-engine pdfplumber if results are unsatisfactory.")

        return "\n".join(report_lines)


def extract_pdf_text(pdf_path: str, engine: str = "pymupdf", page_num: Optional[int] = None) -> str:
    """
    Convenience function to extract PDF text

    Args:
        pdf_path: Path to PDF file
        engine: Extraction engine to use
        page_num: Specific page to extract (None for all)

    Returns:
        Extracted text
    """
    extractor = PDFExtractor(pdf_path, engine)

    if page_num is not None:
        return extractor.preprocess_text(extractor.extract_page(page_num))
    else:
        return extractor.extract_all()
