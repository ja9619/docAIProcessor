from fuzzywuzzy import fuzz

from utils import FORM_15H, FORM_15G

form_15g_keys = [
    "Name of Assessee (Declarant)",
    "PAN of the Assessee",
    "Status",
    "Previous year(P.Y.)",
    "Residential Status",
    "Flat/Door/Block No.",
    "Name of Premises",
    "Road/Street/Lane",
    "Area/Locality",
    "Town/City/District",
    "State",
    "PIN",
    "Email",
    "Telephone No. (with STD Code) and Mobile No.",
    "If yes, latest assessment year for which assessed"
    "Estimated income for which this declaration is made",
    "Estimated total income of the P.Y. in which income mentioned in column 16 to be included",
    "Aggregate amount of income for which Form No.15G filed",
    "Total No. of Form No. 15G filed",
    "Details of income for which the declaration is filed",
]

form_15g_table_keys = [
    "Identification number of relevant investment/account, etc.",
    "Nature of income",
    "Section under which tax is deductible",
    "Amount of income",
]

form_15g_checkbox_keys = [
    "Whether assessed to tax",
]

form_15h_keys = [
    "Name of Assessee (Declarant)",
    "Permanent Account Number or Aadhaar Number of the Assessee",
    "Date of Birth (DD/MM/YYYY)"
    "Previous year(P.Y.) (for which declaration is being made)"
    "Flat/Door/Block No.",
    "Name of Premises",
    "Road/Street/Lane",
    "Area/Locality",
    "Town/City/District",
    "State",
    "PIN",
    "Email",
    "Telephone No. (with STD Code) and Mobile No.",
    "If yes, latest assessment year for which assessed"
    "Estimated income for which this declaration is made",
    "Estimated total income of the P.Y. in which income mentioned in column 15 to be included",
    "Aggregate amount of income for which Form No.15H filed",
    "Total No. of Form No. 15H filed",
    "Details of income for which the declaration is filed",
]

form_15h_table_keys = [
    "Identification number of relevant investment/account, etc.",
    "Nature of income",
    "Section under which tax is deductible",
    "Amount of income",
]

form_15h_checkbox_keys = [
    "Whether assessed to tax",
]

checked_values_list = [
    "yes",
    "no",
]


def is_checked_key(key):
    return True if key in form_15g_table_keys + form_15h_table_keys else False


def get_checked_key(form_type):
    if form_type == FORM_15G:
        return form_15g_table_keys[0]
    elif form_type == FORM_15H:
        return form_15h_table_keys[0]
    else:
        return None


def inspect_form_key(form_type, parsed_key, is_table_key):
    if form_type == FORM_15G:
        keys = form_15g_table_keys if is_table_key else form_15g_keys
    elif form_type == FORM_15H:
        keys = form_15h_table_keys if is_table_key else form_15h_keys
    else:
        return None

    # Use fuzzy matching to find the best match for the key
    best_match_score = 0
    best_match_key = None
    for key in keys:
        score = fuzz.partial_ratio(key, parsed_key)
        if score > best_match_score:
            best_match_score = score
            best_match_key = key

    # Check if the best match is a good enough match
    if best_match_score > 80:
        return best_match_key
    else:
        return None


def get_max_keys_needed(form_type):
    keys = get_all_keys(form_type)
    return len(keys)


def get_all_keys(form_type):
    if form_type == FORM_15G:
        keys = form_15g_keys + form_15g_table_keys + form_15g_checkbox_keys
    elif form_type == FORM_15H:
        keys = form_15h_keys + form_15h_table_keys + form_15h_checkbox_keys
    else:
        return None
    return keys
