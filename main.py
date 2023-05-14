import os
import pandas as pd
from google.cloud import documentai_v1beta3 as documentai
from typing import List, Sequence
import rarfile

PROJECT_ID = "YOUR_PROJECT_ID"
LOCATION = "YOUR_PROJECT_LOCATION"  # Format is 'us' or 'eu'
PROCESSOR_ID = "FORM_PARSER_ID"  # Create processor in Cloud Console
DEBUG_MODE = True
ACCEPTED_CONFIDENCE_THRESHOLD = 0.6


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
    i = 0

    # find whether the document is 15G or 15H
    match_15g = False
    match_15h = False

    results = dict()

    stop_processing = False

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

                if "15H" in name:
                    match_15h = True
                if "15G" in name:
                    match_15g = True

                results[name] = values

            # table data
            for index, table in enumerate(page.tables):
                header_row_values = get_table_data(table.header_rows, document.text)
                body_row_values = get_table_data(table.body_rows, document.text)
                # TODO: get only those columns which are needed

            # extract the OCR text from the Document AI API response
            # may not need
            # for block in page.blocks:
            #     for paragraph in block.paragraphs:
            #         for word in paragraph.words:
            #             print(word.text.content)

        i += 1

    if match_15h ^ match_15g:
        print("tax document type found!")
    else:
        print("error can't decide the tax document type")
        return None

    return results


def process_tax_files(file_path):
    # create a RAR file object
    rar_file = rarfile.RarFile(file_path)

    # resultant dict
    parsed_results = []

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
            continue

        response_dict = parse_document(content, mime_type)
        if response_dict is not None:
            parsed_results.append(response_dict)

    # make the dataframe and convert to excel
    df = pd.DataFrame(parsed_results)
    df.to_excel("output/results.xlsx")


if __name__ == '__main__':
    # give path of the zip file
    process_tax_files("15G.rar")
