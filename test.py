from unittest.mock import patch

# Import your code that interacts with the Google Cloud DocumentAI API
from main import process_tax_files

mock_response = {
    'inputConfig': {
        'gcsSource': {
            'uri': 'gs://bucket/document.pdf',
        },
    },
    'document': {
        'pages': [
            {
                'pageNumber': 1,
                'blocks': [
                    {
                        'layout': {
                            'textAnchor': {
                                'textSegments': [
                                    {
                                        'startOffset': 0,
                                        'endOffset': 10,
                                    },
                                ],
                            },
                        },
                        'paragraphs': [
                            {
                                'layout': {
                                    'textAnchor': {
                                        'textSegments': [
                                            {
                                                'startOffset': 0,
                                                'endOffset': 5,
                                            },
                                        ],
                                    },
                                },
                                'words': [
                                    {
                                        'layout': {
                                            'textAnchor': {
                                                'textSegments': [
                                                    {
                                                        'startOffset': 0,
                                                        'endOffset': 2,
                                                    },
                                                ],
                                            },
                                        },
                                        'content': '15G',
                                    },
                                    {
                                        'layout': {
                                            'textAnchor': {
                                                'textSegments': [
                                                    {
                                                        'startOffset': 3,
                                                        'endOffset': 5,
                                                    },
                                                ],
                                            },
                                        },
                                        'content': 'world',
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        'form_fields': [
                            {
                                'field_name': 'Name of Assessee',
                                'field_value': {
                                    'text_anchor': {
                                        'text_segments': [
                                            {
                                                'start_offset': 0,
                                                'end_offset': 10,
                                            },
                                        ],
                                    },
                                },
                            },
                            {
                                'field_name': 'email',
                                'field_value': {
                                    'text_anchor': {
                                        'text_segments': [
                                            {
                                                'start_offset': 11,
                                                'end_offset': 25,
                                            },
                                        ],
                                    },
                                },
                            },
                        ],
                    },
                ],
            },
        ],
    },
}


def test_process_document():
    # Create a mock response object
    mock_response = {
        'document_text': 'This is the extracted text.',
        'entities': ['entity1', 'entity2'],
        'confidence_score': 0.9
    }

    # Patch the function that makes the API call
    with patch('main.online_process') as mock_make_api_call:
        # Set the return value of the mocked API call to the mock response
        mock_make_api_call.return_value = mock_response

        # Call your code that processes the Google response
        process_tax_files("15G.zip")