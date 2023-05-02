import os
import zipfile
import pandas as pd
from google.cloud import documentai
from typing import List, Sequence

PROJECT_ID = "YOUR_PROJECT_ID"
LOCATION = "YOUR_PROJECT_LOCATION"  # Format is 'us' or 'eu'
PROCESSOR_ID = "FORM_PARSER_ID"  # Create processor in Cloud Console
DEBUG_MODE = True

def online_process(
        project_id: str,
        location: str,
        processor_id: str,
        file_path: str,
        mime_type: str,
) -> documentai.Document:
    """
    Processes a document using the Document AI Online Processing API.
    """

    opts = {"api_endpoint": f"{location}-documentai.googleapis.com"}

    # Instantiates a client
    documentai_client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # The full resource name of the processor, e.g.:
    # projects/project-id/locations/location/processor/processor-id
    # You must create new processors in the Cloud Console first
    resource_name = documentai_client.processor_path(project_id, location, processor_id)

    # Read the file into memory
    with open(file_path, "rb") as image:
        image_content = image.read()

        # Load Binary Data into Document AI RawDocument Object
        raw_document = documentai.RawDocument(
            content=image_content, mime_type=mime_type
        )

        # Configure the process request
        request = documentai.ProcessRequest(
            name=resource_name, raw_document=raw_document
        )

        # Use the Document AI client to process the sample form
        result = documentai_client.process_document(request=request)

        return result.document


def trim_text(text: str):
    """
    Remove extra space characters from text (blank, newline, tab, etc.)
    """
    return text.strip().replace("\n", " ")

def get_table_data(
    rows: Sequence[documentai.Document.Page.Table.TableRow], text: str
) -> List[List[str]]:
    """
    Get Text data from table rows
    """
    all_values: List[List[str]] = []
    for row in rows:
        current_row_values: List[str] = []
        for cell in row.cells:
            current_row_values.append(
                text_anchor_to_text(cell.layout.text_anchor, text)
            )
        all_values.append(current_row_values)
    return all_values


def text_anchor_to_text(text_anchor: documentai.Document.TextAnchor, text: str) -> str:
    """
    Document AI identifies table data by their offsets in the entirety of the
    document's text. This function converts offsets to a string.
    """
    response = ""
    # If a text segment spans several lines, it will
    # be stored in different text segments.
    for segment in text_anchor.text_segments:
        start_index = int(segment.start_index)
        end_index = int(segment.end_index)
        response += text[start_index:end_index]
    return response.strip().replace("\n", " ")

def parse_document(file_name):
    # The local file in your current working directory
    file_path = file_name

    # default mime type
    mime_type = "application/pdf"
    file_extension = os.path.splitext(file_name)[1]
    if file_extension == "jpg":
        mime_type = "image/jpeg"

    # function which calls our DocumentAI API
    document = online_process(
        project_id=PROJECT_ID,
        location=LOCATION,
        processor_id=PROCESSOR_ID,
        file_path=file_path,
        mime_type=mime_type,
    )

    names = []
    name_confidence = []
    values = []
    value_confidence = []

    for page in document.pages:

        # key value pairs
        for field in page.form_fields:
            # Get the extracted field names
            names.append(trim_text(field.field_name.text_anchor.content))
            # Confidence - How "sure" the Model is that the text is correct
            name_confidence.append(field.field_name.confidence)

            values.append(trim_text(field.field_value.text_anchor.content))
            value_confidence.append(field.field_value.confidence)
            # TODO: only extract interested keys and work on them

        # table data
        for index, table in enumerate(page.tables):
            header_row_values = get_table_data(table.header_rows, document.text)
            body_row_values = get_table_data(table.body_rows, document.text)
            # TODO: get only those columns which are needed

        # find whether the document is 15G or 15H
        match_15g = False
        match_15h = False
        for key in names:
            if "15H" in key:
                match_15h = True
            if "15G" in key:
                match_15g = True
        if match_15h ^ match_15g:
            print("tax document type found!")
        else:
            print("error can't decide the tax document type")
            return


def process_tax_files(zip_file):
    # Open the zip file for reading
    zip_read = zipfile.ZipFile(zip_file, mode='r')

    # Inspect the contents of single_file.zip
    files = zip_read.namelist()

    # resultant dict
    parsed_results = []

    for file_name in files:
        response_dict = parse_document(file_name)
        parsed_results.append(response_dict)

    # Close the archive releasing it from memory
    zip_read.close()

    # make the dataframe and convert to excel
    df = pd.DataFrame(parsed_results)
    df.to_excel("output/results.xlsx")


if __name__ == '__main__':
    process_tax_files(None)
