import errno
import os
import re
from pathlib import Path

from google.cloud import documentai

BASE_DIR = Path(__file__).resolve().parent
FORM_15G = "15G"
FORM_15H = "15H"


def trim_text(text: str,is_key: bool):
    """
    Remove extra space characters from text (blank, newline, tab, etc.)
    """
    if is_key:
        # Define the regular expression pattern
        # matches one or more digits (\d+)
        pattern = r'\d+\.'

        # Replace the pattern with an empty string
        modified_text = re.sub(pattern, '', text)

        return modified_text.strip().replace("\n", " ")

    else:
        return text.strip().replace("\n", " ")


def layout_to_text(layout: documentai.Document.Page.Layout, text: str, is_key: bool) -> str:
    """
    Document AI identifies text in different parts of the document by their
    offsets in the entirety of the document's text. This function converts
    offsets to a string.
    """
    response = ""
    # If a text segment spans several lines, it will
    # be stored in different text segments.
    for segment in layout.text_anchor.text_segments:
        start_index = int(segment.start_index)
        end_index = int(segment.end_index)
        response += text[start_index:end_index]
    return trim_text(response, is_key)
