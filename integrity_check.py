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
    from crud import get_tags_with_empty_rfid_tag, get_all_rfid_tags

    # Get all tags with empty rfid_tag from DB sorted by category and name separately
    empty_tags = get_tags_with_empty_rfid_tag()

    for category in sorted(empty_tags.keys()):
        names = empty_tags[category]
        # Sort names alphabetically (numeric categories should be sorted numerically)
        if category == "numeric":
            try:
                sorted_names = sorted(names, key=lambda x: int(x))
            except ValueError:
                sorted_names = sorted(names)
        else:
            sorted_names = sorted(names)

        # Get all RFIDTag objects from DB for the category
        all_tags_for_category = [tag for tag in get_all_rfid_tags() if tag.rfid_type == category]

        # Map name to tag object for quick lookup
        tag_lookup = {tag.name: tag for tag in all_tags_for_category}

        missing_with_ids = []
        for name in sorted_names:
            tag_obj = tag_lookup.get(name)
            if tag_obj:
                missing_with_ids.append((name, tag_obj.id))
            else:
                missing_with_ids.append((name, None))

        if missing_with_ids:
            write_missing_entries_for_category(category, missing_with_ids)

    # Reload all tags from DB after processing
    file_lib.load_all_tags()


def any_missing_entries():
    missing = find_missing_entries()
    return any(len(v) > 0 for v in missing.values())
