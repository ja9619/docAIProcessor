import logging
import os
import pandas as pd
from google.cloud import documentai_v1beta3 as documentai
import rarfile
import form_keys
from utils import trim_text, BASE_DIR, FORM_15G, FORM_15H

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
    ocr_feature = documentai.types.DocumentUnderstandingConfig.Feature(
        type=documentai.enums.Feature.Type.DOCUMENT_TEXT_DETECTION)

    features = [key_value_pair_feature, table_feature, ocr_feature]

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


def parse_document(content, mime_type):
    # page pointer
    page_number = 1

    # find whether the document is 15G or 15H
    form_type = ""

    results = dict()

    stop_processing = False
    count_keys = 0

    while not stop_processing:
        # function which calls our DocumentAI API
        document = online_process(
            project_id=PROJECT_ID,
            location=LOCATION,
            processor_id=PROCESSOR_ID,
            file_content=content,
            mime_type=mime_type,
            page_number=page_number
        )

        for page in document.pages:

            # extract the OCR text to determine the tax form type
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        if FORM_15G.lower() in word.lower():
                            form_type = FORM_15G
                            break
                        elif FORM_15H.lower() in word.lower():
                            form_type = FORM_15H
                            break
                        elif form_type != "":
                            # found the form type, don't dig deeper
                            break

            if form_type != "":
                logger.debug(f'tax document type found to be: {form_type}!')
            else:
                logger.warning("error can't decide the tax document type.")
                # only try till second page to find the document type
                if page_number < 2:
                    page_number += 1
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

                # handle checked keys
                if name.lower() in form_keys.checked_values_list and values.lower() in ["true", "checked"]:
                    official_form_key = form_keys.get_checked_key(form_type)
                    if official_form_key is not None:
                        results[official_form_key] = name if results[official_form_key] == "" else "Unknown"
                        count_keys += 1
                    continue

                # get the official field in the form which corresponds to this field name
                official_form_key = form_keys.inspect_form_key(name, form_type, False)
                if official_form_key is not None:
                    if form_keys.is_checked_key(official_form_key):
                        results[official_form_key] = field.field_value.text.lower() in ["true", "checked"]
                    else:
                        results[official_form_key] = values

                    count_keys += 1
                else:
                    logger.warning(f'key: {name} not found under form keys')

            # table data
            for index, table in enumerate(page.tables):
                header_cells = table.header_rows[0].cells
                for cell in header_cells:
                    official_table_key = form_keys.inspect_form_key(cell.layout.text, form_type, True)
                    if official_table_key is not None:
                        count_keys += 1
                        # If a match is found, extract the corresponding column data
                        col_idx = header_cells.index(cell)
                        col_data = [row.cells[col_idx].layout.text for row in table.body_rows]
                        results[official_table_key] = col_data
                    else:
                        logger.warning(f'key: {cell.layout.text} not found under form keys')

        # don't go more than 3 pages
        if page_number >= 3 or count_keys >= form_keys.get_max_keys_needed(form_type):
            stop_processing = True

        # go to the next page
        page_number += 1

    return results, form_type


def process_tax_files(file_path):
    # create a RAR file object
    rar_file = rarfile.RarFile(file_path)

    # excel path
    base_path = os.path.join(BASE_DIR, 'output')
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    file_name = f"{file_path}-results.xlsx"
    excel_file_path = os.path.join(base_path, file_name)

    try:
        writer = pd.ExcelWriter(excel_file_path, engine="openpyxl", mode="a", if_sheet_exists="overlay")
    except FileNotFoundError as e:
        print(f"Error: {e}. The specified directory or file does not exist.")

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

        # Add headers to the worksheet
        if not headers_defined:
            headers = form_keys.get_all_keys(form_type)
            if headers is None:
                logger.error(f'cannot make the excel sheet headers for file: {file_name}')
                continue

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
