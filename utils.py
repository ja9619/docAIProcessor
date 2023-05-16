import errno
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FORM_15G = "15G"
FORM_15H = "15H"

def trim_text(text: str):
    """
    Remove extra space characters from text (blank, newline, tab, etc.)
    """
    return text.strip().replace("\n", " ")
