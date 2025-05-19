from pathlib import Path

import file_lib
from tagwriter import write_missing_entries_for_category


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


def get_assigned_entries():
    actions_db, figures_db, gamer_figures_db, animal_figures_db, animal_numbers_db = file_lib.group_tags_by_type()

    return {
        "actions": set(getattr(tag, "name", None) for tag in actions_db.values()),
        "animals": set(getattr(tag, "name", None) for tag in animal_figures_db.values()),
        "figures": set(getattr(tag, "name", None) for tag in figures_db.values()),
        "games": set(getattr(tag, "name", None) for tag in gamer_figures_db.values()),
        "numeric": set(getattr(tag, "number", None) for tag in animal_numbers_db.values()),
    }


def find_missing_entries():
    expected = get_expected_entries()
    assigned = get_assigned_entries()
    # 'None' entfernen, falls beim ersten Mal Füllen durch getattr 'None' vorkommt
    missing = {
        cat: {
            val for val in expected[cat] if val and val not in assigned.get(cat, set())
        }
        for cat in expected
    }
    return missing


def remap_missing_entries():
    missing_entries = find_missing_entries()
    for cat, missing_names in missing_entries.items():
        if missing_names:
            write_missing_entries_for_category(cat, missing_names)
            # Reload from DB to update
            file_lib.load_all_tags()


def any_missing_entries():
    missing = find_missing_entries()
    return any(len(v) > 0 for v in missing.values())
