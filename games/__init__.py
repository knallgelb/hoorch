from . import game_animals_english
from . import game_aufnehmen
from . import game_einmaleins
from . import game_geschichten_aufnehmen
from . import game_geschichten_abspielen
from . import game_hoerspiele
from . import game_kakophonie
from . import game_tier_orchester
from . import game_tierlaute

games = {
    "Aufnehmen": game_geschichten_aufnehmen,
    "Abspielen": game_geschichten_abspielen,
    "Tierlaute": game_tierlaute,
    "TierOrchester": game_tier_orchester,
    "Kakophonie": game_kakophonie,
    "Einmaleins": game_einmaleins,
    "Animals": game_animals_english
}