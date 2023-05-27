import json
import unittest
from unittest.mock import patch
import main

mock_response = {
    "text": '15G Name of Assesee (Declarant) PARTH PAN of Assesse 12345 Status Single Twn/City/District parel',
    "pages": [
        {
            'pageNumber': 1,
            'form_fields': [
                {
                    'field_name': {
                        'text_anchor': {
                            'text_segments': [
                                {
                                    'start_index': 4,
                                    'end_index': 30,
                                },
                            ],
                        },
                        'confidence': 0.9,
                    },
                    'field_value': {
                        'text_anchor': {
                            'text_segments': [
                                {
                                    'start_index': 31,
                                    'end_index': 36,
                                },
                            ],
                        },
                        'confidence': 0.9,
                    },
                },
            ],
        }
    ],
}


class DocumentAITestCase(unittest.TestCase):
    def test_process_document(self):
        with open("config.json") as json_data_file:
            main.config_data = json.load(json_data_file)

        # Patch the function that makes the API call
        with patch('main.online_process') as mock_make_api_call:
            # Set the return value of the mocked API call to the mock response
            mock_make_api_call.return_value = mock_response

            # Call your code that processes the Google response
            main.process_tax_files("15G.zip")


if __name__ == '__main__':
    unittest.main()
