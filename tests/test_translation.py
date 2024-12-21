import os
import pytest

@pytest.mark.parametrize("locale, expected_translation", [
    ("de", "Sie befinden sich im Admin-Menü."),
    ("en", "You are in the admin menu."),
])
def test_translator(locale, expected_translation, translator_factory):
    # Arrange: Create a Translator for the given locale
    translator = translator_factory(locale)

    # Act: Translate the text
    translation = translator.translate("admin.admin_menu")

    # Assert: Check the translation
    assert translation == expected_translation, f"Expected {expected_translation}, but got {translation}"
