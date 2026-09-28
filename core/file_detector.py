# Project Midas — File Type Detector
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Determines the actual file type using magic bytes (file header signatures)
cross-referenced against the filename extension.

Magic bytes are trusted over extensions — a PDF renamed to .xlsx will be
correctly identified as a PDF.

Returns one of: "pdf", "xlsx", "csv", "docx", "image", "txt", "unknown"
"""

import logging
import os

logger = logging.getLogger(__name__)

# Magic byte signatures (first N bytes of the file)
_SIGNATURES = [
    # (magic_bytes, offset, detected_type)
    (b"%PDF",          0, "pdf"),
    (b"\x89PNG\r\n",   0, "image"),    # PNG
    (b"\xff\xd8\xff",  0, "image"),    # JPEG
    (b"GIF87a",        0, "image"),    # GIF87
    (b"GIF89a",        0, "image"),    # GIF89
    (b"BM",            0, "image"),    # BMP
    (b"II\x2a\x00",    0, "image"),    # TIFF (little-endian)
    (b"MM\x00\x2a",    0, "image"),    # TIFF (big-endian)
    (b"PK\x03\x04",    0, "zip"),     # ZIP container (xlsx, docx, pptx)
]

# Extensions that map to file types (used as fallback and for ZIP disambiguation)
_EXT_MAP = {
    ".pdf":  "pdf",
    ".xlsx": "xlsx",
    ".xls":  "xlsx",
    ".csv":  "csv",
    ".tsv":  "csv",
    ".docx": "docx",
    ".doc":  "docx",
    ".txt":  "txt",
    ".png":  "image",
    ".jpg":  "image",
    ".jpeg": "image",
    ".gif":  "image",
    ".bmp":  "image",
    ".tiff": "image",
    ".tif":  "image",
}


def _check_zip_contents(file_path: str) -> str:
    """Disambiguate a ZIP container into xlsx, docx, or generic zip."""
    import zipfile
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            names = zf.namelist()
            # xlsx: contains xl/workbook.xml or xl/worksheets/
            if any(n.startswith("xl/") for n in names):
                return "xlsx"
            # docx: contains word/document.xml
            if any(n.startswith("word/") for n in names):
                return "docx"
            # pptx or other
            return "unknown"
    except (zipfile.BadZipFile, Exception):
        return "unknown"


def _is_likely_csv(file_path: str) -> bool:
    """Heuristic: first 3 lines contain commas or tabs consistently."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = []
            for _ in range(3):
                line = f.readline()
                if not line:
                    break
                lines.append(line)
        if not lines:
            return False
        # Check if all lines have the same delimiter count (comma or tab)
        for delim in (",", "\t"):
            counts = [line.count(delim) for line in lines]
            if all(c > 0 for c in counts):
                return True
        return False
    except Exception:
        return False


def detect_file_type(file_path: str) -> str:
    """
    Detect the actual file type using magic bytes, then cross-reference
    with the filename extension.

    Returns: "pdf", "xlsx", "csv", "docx", "image", "txt", "unknown"
    """
    if not file_path or not os.path.exists(file_path):
        return "unknown"

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return "unknown"

    # 1. Read magic bytes
    magic_type = None
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
        for sig, offset, ftype in _SIGNATURES:
            if header[offset:offset + len(sig)] == sig:
                magic_type = ftype
                break
    except Exception as e:
        logger.warning(f"Failed to read magic bytes from {file_path}: {e}")

    # 2. Get extension-based type
    ext = os.path.splitext(file_path)[1].lower()
    ext_type = _EXT_MAP.get(ext, "unknown")

    # 3. Cross-reference
    if magic_type == "zip":
        # Disambiguate ZIP containers
        magic_type = _check_zip_contents(file_path)

    if magic_type is not None:
        # Magic bytes found — trust them
        if ext_type != "unknown" and ext_type != magic_type:
            logger.warning(
                f"File type mismatch for {file_path}: "
                f"magic bytes say '{magic_type}' but extension says '{ext_type}'. "
                f"Trusting magic bytes."
            )
        return magic_type

    # 4. No magic bytes matched — fall back to extension + heuristics
    if ext in (".csv", ".tsv"):
        if _is_likely_csv(file_path):
            return "csv"
        return "txt"  # Has .csv extension but doesn't look like CSV

    if ext in (".txt",):
        return "txt"

    # Last resort: check if it's a text file
    if _is_likely_csv(file_path):
        return "csv"

    return ext_type if ext_type != "unknown" else "unknown"


def get_file_type_description(file_type: str) -> str:
    """Human-readable description for the classifier prompt."""
    descriptions = {
        "pdf":     "PDF document (text-based, not a spreadsheet)",
        "xlsx":    "Excel spreadsheet (.xlsx)",
        "csv":     "CSV/TSV tabular data file",
        "docx":    "Microsoft Word document",
        "image":   "Image file (photo, screenshot, or diagram)",
        "txt":     "Plain text file",
        "unknown": "Unknown file format",
    }
    return descriptions.get(file_type, "Unknown file format")
