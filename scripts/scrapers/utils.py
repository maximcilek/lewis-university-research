import re


### UTILS/HELPERS ###
def normalize_string(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()

def build_dict(seq, key):
    return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))

def merge_string_arrays_by_index(arr1, arr2):
    result = []
    for i in range(len(arr1)):
        v1 = arr1[i]
        v2 = arr2[i]
        if not (v1 is None or (isinstance(v1, str) and v1.strip() == "")):
            result.append(v1)
        elif not (v2 is None or (isinstance(v2, str) and v2.strip() == "")):
            result.append(v2)
        else:
            result.append(None)
    return result

def javascript_variable_exists(text: str, var_name: str) -> bool:
    return re.search(rf'\b(var|let|const)\s+{re.escape(var_name)}\s*=', text) is not None

def extract_javascript_variables(text: str, variable_names: list[str]) -> dict:
    data = {}
    for var_name in variable_names:
        match = re.search(rf'\b(var|let|const)\s+{re.escape(var_name)}\s*=\s*(.*?);', text, re.DOTALL)
        if not match:
            data[var_name] = None
            continue
        value = match.group(2).strip()
        # ARRAY DETECTION (ONLY HERE)
        if value.startswith("[") and value.endswith("]"):
            data[var_name] = extract_html_javascript_array(text, var_name)
            continue
        # STRING CLEANUP
        if (len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"')):
            inner = value[1:-1]
            data[var_name] = None if inner == "" else inner
            continue
        # DEFAULT
        data[var_name] = value
    return data

def extract_html_javascript_array(text, variable_name):
    match = re.search(rf"var {re.escape(variable_name)}\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        LOGGER.debug("HTML JavaScript array (%s) not found: %s", variable_name, text)
        return None
    try:
        return json.loads(match.group(1)) # normalized = raw.replace("'", '"')
    except Exception as e:
        LOGGER.exception("Failed to extract HTML JavaScript array: %s", e)
        raise
