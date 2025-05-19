from pathlib import Path

import file_lib


def load_reference_set(category):
    path = Path("figures") / f"{category}.txt"
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def get_expected_entries():
    categories = ["actions", "animals", "figures", "games", "numeric"]
    expected = dict()
    for cat in categories:
        expected[cat] = load_reference_set(cat)
    return expected


from crud import get_tags_with_empty_rfid_tag

def get_assigned_entries():
    """
    Returns the names of tags per category that have empty rfid_tag in database,
    i.e. where the actual RFID number/tag is missing.
    """
    empty_tags = get_tags_with_empty_rfid_tag()
    result = {}
    for category, names in empty_tags.items():
        result[category] = set(names)
    return result


def find_missing_entries():
    expected = get_expected_entries()
    assigned = get_assigned_entries()
    # 'None' entfernen, falls beim ersten Mal Füllen durch getattr 'None' vorkommt
    missing = {
        cat: {
            val for val in expected[cat] if val and val in assigned.get(cat, set())
        }
        for cat in expected
    }
    return missing


def remap_missing_entries():
    from tagwriter import write_missing_entries_for_category
    from crud import get_all_rfid_tags

    missing_entries = find_missing_entries()

    # Get all RFIDTag objects from DB
    all_tags = get_all_rfid_tags()

    # Map name and category to RFIDTag object for quick lookup
    tag_lookup = {}
    for tag in all_tags:
        tag_lookup[(tag.rfid_type, tag.name)] = tag

    for cat, missing_names in missing_entries.items():
        if missing_names:
            # Prepare list of tuples (name, RFIDTag ID) for missing
            missing_with_ids = []
            for name in missing_names:
                tag_obj = tag_lookup.get((cat, name))
                if tag_obj:
                    missing_with_ids.append((name, tag_obj.id))
                else:
                    # If no tag found, append with None as id
                    missing_with_ids.append((name, None))

            write_missing_entries_for_category(cat, missing_with_ids)
            # Reload from DB to update
            file_lib.load_all_tags()


def any_missing_entries():
    missing = find_missing_entries()
    return any(len(v) > 0 for v in missing.values())
