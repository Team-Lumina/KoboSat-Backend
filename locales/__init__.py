# Locale map — maps language code to locale module
from locales import en, yo, ha, ig

LOCALE_MAP = {
    "en": en,
    "yo": yo,
    "ha": ha,
    "ig": ig,
}


def get_locale(language: str):   #Return the locale module for a given language code. Falls back to English if language not found.
    return LOCALE_MAP.get(language, en)