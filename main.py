import logging

import pandas as pd
from google.cloud import documentai_v1beta3 as documentai
from typing import List, Sequence
import rarfile

from form_keys import inspect_form_key, form_15g_keys, form_15h_keys

PROJECT_ID = "YOUR_PROJECT_ID"
LOCATION = "YOUR_PROJECT_LOCATION"  # Format is 'us' or 'eu'
PROCESSOR_ID = "FORM_PARSER_ID"  # Create processor in Cloud Console
DEBUG_MODE = True
ACCEPTED_CONFIDENCE_THRESHOLD = 0.6

logger = logging.getLogger(__name__)


def online_process(
        project_id: str,
        location: str,
        processor_id: str,
        file_content: any,
        mime_type: str,
        page_number: int
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

    # specify the Document AI request object
    document = {"content": file_content, "mime_type": mime_type}

    # specify the features to extract from the document
    key_value_pair_feature = documentai.types.DocumentUnderstandingConfig.Feature(
        type=documentai.enums.Feature.Type.KEY_VALUE_PAIRS)
    table_feature = documentai.types.DocumentUnderstandingConfig.Feature(
        type=documentai.enums.Feature.Type.TABLES)
    # ocr_feature = documentai.types.DocumentUnderstandingConfig.Feature(
    #     type=documentai.enums.Feature.Type.DOCUMENT_TEXT_DETECTION)

    features = [key_value_pair_feature, table_feature]

    config = documentai.DocumentUnderstandingConfig(feature=features, pages=page_number)

    # Configure the process request
    request = documentai.ProcessDocumentRequest(
        parent=resource_name,
        document=document,
        document_understanding_config=config
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


def parse_document(content, mime_type):
    # page pointer
    i = 1

    # find whether the document is 15G or 15H
    form_type = ""

    results = dict()

    stop_processing = False
    count_keys = 0
    found_all_keys = False

    while not stop_processing:
        # function which calls our DocumentAI API
        document = online_process(
            project_id=PROJECT_ID,
            location=LOCATION,
            processor_id=PROCESSOR_ID,
            file_content=content,
            mime_type=mime_type,
            page_number=i
        )

        for page in document.pages:

            # extract the OCR text from the Document AI API response
            for block in page.blocks:
                if form_type != "":
                    for paragraph in block.paragraphs:
                        if form_type != "":
                            for word in paragraph.words:
                                if "15H" in word:
                                    form_type = "15H"
                                    break
                                elif "15G" in word:
                                    form_type = "15G"
                                    break

            if form_type != "":
                logger.debug("tax document type found!")
            else:
                logger.warning("error can't decide the tax document type.")
                # only try till second page
                if i < 2:
                    i += 1
                    logger.debug("Going to the next page to find the document type")
                    continue
                return None

            # key value pairs
            for field in page.form_fields:
                # Get the extracted field names
                name = trim_text(field.field_name.text_anchor.content)

                # Confidence - How "sure" the Model is that the text is correct
                name_confidence = field.field_name.confidence

                if name_confidence < ACCEPTED_CONFIDENCE_THRESHOLD:
                    continue

                values = trim_text(field.field_value.text_anchor.content)
                value_confidence = field.field_value.confidence

                if value_confidence < ACCEPTED_CONFIDENCE_THRESHOLD:
                    continue

                official_form_key = inspect_form_key(name, form_type)
                if official_form_key is not None:
                    results[official_form_key] = values
                    count_keys += 1
                else:
                    logger.warning(f'key: {name} not found under form keys')

            # table data
            for index, table in enumerate(page.tables):
                header_row_values = get_table_data(table.header_rows, document.text)
                body_row_values = get_table_data(table.body_rows, document.text)
                # TODO: get only those columns which are needed

        # don't go more than 3 pages
        if i >= 3 or found_all_keys:
            stop_processing = True

        # go to the next page
        i += 1

    return results, form_type


def process_tax_files(file_path):
    # create a RAR file object
    rar_file = rarfile.RarFile(file_path)

    # excel path
    path = f'output/{file_path}-results.xlsx'
    writer = pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="overlay")

    headers_defined = False

    # loop through all files in the extracted folder
    for file_name in rar_file.namelist():
        content = rar_file.read(file_name)

        # default mime type
        mime_type = "application/pdf"

        # ignore any non-PDF or jpg files
        if file_name.endswith(".pdf"):
            mime_type = "application/pdf"
        elif file_name.endswith(".jpg"):
            mime_type = "image/jpeg"
        else:
            logger.warning(f'cannot find the mime type for the file: {file_name}')
            continue

        response_dict, form_type = parse_document(content, mime_type)

        if form_type == "15G":
            headers = form_15g_keys
        elif form_type == "15H":
            headers = form_15h_keys
        else:
            logger.error(f'cannot find the form type for file: {file_name}')
            continue

        # Add headers to the worksheet
        if not headers_defined:
            for i, header in enumerate(headers):
                writer.cell(row=1, column=i + 1, value=header)
            headers_defined = True

        if response_dict is None:
            logger.error(f'couldnt get values for the file:{file_name}')
            continue

        # Write the dictionary values to the sheet
        for key, value in response_dict.items():
            # Find the column index for the key
            try:
                col_index = headers.index(key) + 1
            except ValueError:
                logger.error(f'cannot find the entry in form keys for column:{key}')
                continue  # Skip keys not found in columns

            # Write the value to the cell in the corresponding row and column
            row_index = writer.max_row + 1
            writer.cell(row=row_index, column=col_index, value=value)
            writer.save()

    logger.debug(f'finished processing of the tax files under: {file_path}')


if __name__ == '__main__':
    # give path of the zip file
    process_tax_files("15G.rar")
    process_tax_files("15H.rar")
