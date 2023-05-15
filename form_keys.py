from fuzzywuzzy import fuzz

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
    "Whether assessed to tax",
    "If yes, latest assessment year for which assessed"
    "Estimated income for which this declaration is made",
    "Estimated total income of the P.Y. in which income mentioned in column 16 to be included",
    "Aggregate amount of income for which Form No.15G filed",
    "Total No. of Form No. 15G filed",
    "Details of income for which the declaration is filed",
    "Identification number of relevant investment/account, etc.",
    "Nature of income",
    "Section under which tax is deductible",
    "Amount of income",
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
    "Whether assessed to tax",
    "If yes, latest assessment year for which assessed"
    "Estimated income for which this declaration is made",
    "Estimated total income of the P.Y. in which income mentioned in column 15 to be included",
    "Aggregate amount of income for which Form No.15H filed",
    "Total No. of Form No. 15H filed",
    "Details of income for which the declaration is filed",
    "Identification number of relevant investment/account, etc.",
    "Nature of income",
    "Section under which tax is deductible",
    "Amount of income",
]


def inspect_form_key(form_type, key_found):
    if form_type == "15G":
        keys = form_15g_keys
    elif form_type == "15H":
        keys = form_15h_keys
    else:
        return None

    # Use fuzzy matching to find the best match for the key
    best_match_score = 0
    best_match_key = None
    for key in keys:
        score = fuzz.partial_ratio(key, key_found)
        if score > best_match_score:
            best_match_score = score
            best_match_key = key

    # Check if the best match is a good enough match
    if best_match_score > 80:
        return best_match_key
    else:
        return None
