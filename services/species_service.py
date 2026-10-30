# services/species_service.py - finds the scientific species name from a tree name
import re

# common name (lowercase)  ->  scientific name
# Add more lines here any time you need more trees.
SPECIES_MAP = {
    "neem": "Azadirachta indica",
    "mango": "Mangifera indica",
    "banyan": "Ficus benghalensis",
    "peepal": "Ficus religiosa",
    "pipal": "Ficus religiosa",
    "bodhi": "Ficus religiosa",
    "gulmohar": "Delonix regia",
    "gulmohur": "Delonix regia",
    "flame tree": "Delonix regia",
    "tamarind": "Tamarindus indica",
    "imli": "Tamarindus indica",
    "pongamia": "Pongamia pinnata",
    "karanja": "Pongamia pinnata",
    "indian beech": "Pongamia pinnata",
    "jamun": "Syzygium cumini",
    "black plum": "Syzygium cumini",
    "teak": "Tectona grandis",
    "coconut": "Cocos nucifera",
    "banana": "Musa acuminata",
    "guava": "Psidium guajava",
    "lemon": "Citrus limon",
    "orange": "Citrus sinensis",
    "papaya": "Carica papaya",
    "jackfruit": "Artocarpus heterophyllus",
    "sandalwood": "Santalum album",
    "eucalyptus": "Eucalyptus globulus",
    "bamboo": "Bambusa vulgaris",
    "arjuna": "Terminalia arjuna",
    "ashoka": "Saraca asoca",
    "false ashoka": "Polyalthia longifolia",
    "mast tree": "Polyalthia longifolia",
    "mahogany": "Swietenia mahagoni",
    "rain tree": "Samanea saman",
    "raintree": "Samanea saman",
    "copper pod": "Peltophorum pterocarpum",
    "copperpod": "Peltophorum pterocarpum",
    "silver oak": "Grevillea robusta",
    "casuarina": "Casuarina equisetifolia",
    "babul": "Vachellia nilotica",
    "acacia": "Vachellia nilotica",
    "subabul": "Leucaena leucocephala",
    "mahua": "Madhuca longifolia",
    "amla": "Phyllanthus emblica",
    "gooseberry": "Phyllanthus emblica",
    "moringa": "Moringa oleifera",
    "drumstick": "Moringa oleifera",
    "curry leaf": "Murraya koenigii",
    "cashew": "Anacardium occidentale",
    "pomegranate": "Punica granatum",
    "sapota": "Manilkara zapota",
    "chikoo": "Manilkara zapota",
    "custard apple": "Annona squamosa",
    "mulberry": "Morus alba",
    "amaltas": "Cassia fistula",
    "golden shower": "Cassia fistula",
    "kadamba": "Neolamarckia cadamba",
    "bael": "Aegle marmelos",
    "date palm": "Phoenix dactylifera",
    "royal palm": "Roystonea regia",
    "palmyra": "Borassus flabellifer",
    "toddy palm": "Borassus flabellifer",
    "indian almond": "Terminalia catappa",
    "badam": "Terminalia catappa",
    "pine": "Pinus roxburghii",
    "deodar": "Cedrus deodara",
    "weeping fig": "Ficus benjamina",
    "rubber": "Hevea brasiliensis",
    "gliricidia": "Gliricidia sepium",
    "tabebuia": "Tabebuia rosea",
    "pink trumpet": "Tabebuia rosea",
    "african tulip": "Spathodea campanulata",
    "bottlebrush": "Callistemon citrinus",
    "sirisa": "Albizia lebbeck",
    "siris": "Albizia lebbeck",
    "ber": "Ziziphus mauritiana",
    "jujube": "Ziziphus mauritiana",
    "fig": "Ficus carica",
    "anjeer": "Ficus carica",
    "gular": "Ficus racemosa",
    "cluster fig": "Ficus racemosa",
    "lychee": "Litchi chinensis",
    "jacaranda": "Jacaranda mimosifolia",
    "frangipani": "Plumeria rubra",
    "champa": "Plumeria rubra",
    "hibiscus": "Hibiscus rosa-sinensis",
    "mandarin": "Citrus reticulata",
    "sweet lime": "Citrus limetta",
    "mosambi": "Citrus limetta",
}

# Longest names first, so "false ashoka" is checked before "ashoka"
_KEYS = sorted(SPECIES_MAP, key=len, reverse=True)


def find_species(tree_name):
    """Returns the scientific name for a tree name like 'Neem Tree', or None."""
    name = (tree_name or "").lower().strip()
    if not name:
        return None
    for key in _KEYS:
        # \b makes sure 'mango' does not match inside 'mangosteen'
        if re.search(r"\b" + re.escape(key) + r"\b", name):
            return SPECIES_MAP[key]
    return None