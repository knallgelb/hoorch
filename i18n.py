import os
import yaml

class Translator:
    def __init__(self, locale, translation_dir='translations'):
        """
        Initialize the Translator with a specific locale.
        :param locale: Language code (e.g., 'en', 'de').
        :param translation_dir: Directory containing YAML translation files.
        """
        self.locale = locale
        self.translation_dir = translation_dir
        self.translations = self._load_translations()

    def _load_translations(self):
        """Load translations from the YAML file for the specified locale."""
        file_path = os.path.join(os.path.dirname(__file__), self.translation_dir, f"{self.locale}.yaml")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Translation file not found: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            # Extract translations for the current locale
            return data.get(self.locale, {})

    def translate(self, key, **kwargs):
        """
        Translate a given text with optional formatting arguments.
        :param key: Key to translate (e.g., 'admin.admin_menu').
        :param kwargs: Optional formatting arguments for the text.
        :return: Translated and formatted text.
        """
        keys = key.split('.')  # Split the key into parts for nested lookup
        translation = self.translations
        for k in keys:
            translation = translation.get(k, {})
            if not translation:
                return key  # Fallback to the original key if not found

        if isinstance(translation, str):
            return translation.format(**kwargs)
        return key  # Fallback to the original key if translation is not a string

