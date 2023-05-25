import logging
import os
import uuid
import zipfile
import json
import xlsxwriter
from google.cloud import documentai
import form_keys
from utils import layout_to_text, BASE_DIR, FORM_15G, FORM_15H
from google.api_core.client_options import ClientOptions

logger = logging.getLogger(__name__)


def online_process(
        file_content: any,
        mime_type: str,
) -> documentai.Document:
    """
    Processes a document using the Document AI Online Processing API.
    """
    location = config_data['credentials']['location']
    project_id = config_data['credentials']['project_id']
    processor_id = config_data['credentials']['processor_id']

    # You must set the api_endpoint if you use a location other than 'us'.
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    # Instantiates a client
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # The full resource name of the processor, e.g.:
    # projects/project_id/locations/location/processor/processor_id
    name = client.processor_path(project_id, location, processor_id)

    # Load Binary Data into Document AI RawDocument Object
    raw_document = documentai.RawDocument(content=file_content, mime_type=mime_type)

    # Configure the process request
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    # Use the Document AI client to process the sample form
    result = client.process_document(request=request)
    logger.debug(f'obtained response: {result.document}')
    return result.document


def parse_document(content, mime_type):
    # find whether the document is 15G or 15H
    form_type = ""

    results = dict()
    count_keys = 0
    page_number = 1

    # function which calls our DocumentAI API
    document = online_process(file_content=content, mime_type=mime_type)
    text = document.text

    for page in document.pages:
        if page_number == 4:
            break

        # for block in page.blocks:
        #     # extract the OCR text to determine the tax form type
        #     for paragraph in block.paragraphs:
        #         for word in paragraph.words:
        #             if FORM_15G.lower() in word.lower():
        #                 form_type = FORM_15G
        #                 break
        #             elif FORM_15H.lower() in word.lower():
        #                 form_type = FORM_15H
        #                 break
        #             elif form_type != "":
        #                 # found the form type, don't dig deeper
        #                 break

        if FORM_15G in text:
            form_type = FORM_15G
        elif FORM_15H in text:
            form_type = FORM_15H

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
            name = layout_to_text(field.field_name, text)

            # Confidence - How "sure" the Model is that the text is correct
            name_confidence = field.field_name.confidence
            if name_confidence < config_data['acceptance']['key_threshold']:
                continue

            values = layout_to_text(field.field_name, text)
            value_confidence = field.field_value.confidence
            if value_confidence < config_data['acceptance']['value_threshold']:
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
                results[official_form_key] = values
                count_keys += 1
            else:
                logger.warning(f'key: {name} not found under form keys')

        # table data
        for index, table in enumerate(page.tables):
            header_cells = table.header_rows[0].cells
            for cell in header_cells:
                cell_text = layout_to_text(cell.layout, text)
                official_table_key = form_keys.inspect_form_key(cell_text, form_type, True)
                if official_table_key is not None:
                    count_keys += 1
                    # If a match is found, extract the corresponding column data
                    col_idx = header_cells.index(cell)
                    col_data = [layout_to_text(row.cells[col_idx].layout, text) for row in table.body_rows]
                    results[official_table_key] = col_data
                else:
                    logger.warning(f'key: {cell.layout.text} not found under form keys')

        page_number += 1

    return results, form_type


def process_tax_files(zip_file_path):
    # output excel path
    base_path = os.path.join(BASE_DIR, 'output')
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    excel_file_name = f"{str(uuid.uuid4())}-results.xlsx"
    excel_file_path = os.path.join(base_path, excel_file_name)

    try:
        workbook = xlsxwriter.Workbook(excel_file_path)
    except FileNotFoundError as e:
        print(f"Error: {e}. The specified directory or file does not exist.")
        return

    worksheet = workbook.add_worksheet("Tax Data")

    # Add text wrapping format to the cells
    wrap_format = workbook.add_format({"text_wrap": True})
    worksheet.set_column("A:Z", None, wrap_format)

    headers_defined = False

    # loop through all files in the zip folder
    with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
        for file_name in zip_file.namelist():
            with zip_file.open(file_name) as cur_file:
                file_content = cur_file.read()

                # ignore any non-PDF or jpg files
                if file_name.endswith(".pdf"):
                    mime_type = "application/pdf"
                elif file_name.endswith(".jpg"):
                    mime_type = "image/jpeg"
                else:
                    logger.warning(f'cannot find the mime type for the file: {file_name}')
                    continue

                response_dict, form_type = parse_document(file_content, mime_type)
                if response_dict is None:
                    logger.error(f'could not get values for the file:{file_name}')
                    continue

                # Add headers to the worksheet once
                headers = form_keys.get_all_keys(form_type)
                if headers is None:
                    logger.error(f'cannot make the excel sheet headers for file: {file_name}')
                    continue
                if not headers_defined:
                    for i, header in enumerate(headers):
                        worksheet.write(row=1, column=i + 1, value=header)
                    headers_defined = True

                # Write the dictionary values to the sheet
                for key, value in response_dict.items():
                    # Find the column index for the key
                    try:
                        col_index = headers.index(key) + 1
                    except ValueError:
                        logger.error(f'cannot find the entry in form keys for column:{key}')
                        continue  # Skip keys not found in columns

                    # Write the value to the cell in the corresponding row and column
                    row_index = worksheet.max_row + 1
                    worksheet.cell(row=row_index, column=col_index, value=value)

    workbook.close()
    logger.debug(f'finished processing of the tax files under: {zip_file_path}')


if __name__ == '__main__':
    global config_data
    with open("config.json") as json_data_file:
        config_data = json.load(json_data_file)

    for file in config_data['files']:
        process_tax_files(os.path.join(BASE_DIR, file))
