def map_matches(matches):
    global COUNT_BAD_MATCHES
    clean_matches = []
    for m in matches:
        if m is not None:
            if len(m) == len(MATCH_ATTRIBUTES):  # Ensure length matches the header
                match_clean = {k: m[c] for c, k in enumerate(MATCH_ATTRIBUTES)}
                clean_matches.append(match_clean)
            elif len(m) == 27:  # If the match has 27 items
                if not any(item.strip() == '' for item in m):
                    print(f"Full Match 27 Length ({paramname}): {len(m)} Expected {len(MATCH_ATTRIBUTES)} - {m}")
                    quit()
                # Insert 17 empty strings before the matchid (which should be the last element)
                m = m[:26] + [''] * 17 + [m[26]]
                match_clean = {k: m[c] for c, k in enumerate(MATCH_ATTRIBUTES)}
                clean_matches.append(match_clean)
            else:
                COUNT_BAD_MATCHES += 1
                print(f"Invalid Match: {len(m)} Expected {len(MATCH_ATTRIBUTES)} - {m}")
    return clean_matches