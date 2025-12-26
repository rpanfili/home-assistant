# -*- coding: utf-8 -*-
"""Silea waste pickup constants."""

API_HOST = "www.sileaspa.it"
API_BASE_URI = "/wp-admin/admin-ajax.php"

WASTE_TYPE_NON_RECYCLABLE = "Non-recyclable"
WASTE_TYPE_ORGANIC = "Organic"
WASTE_TYPE_PAPER = "Paper"
WASTE_TYPE_PLASTIC = "Plastic"
WASTE_TYPE_GLASS = "Glass"
STREET_CLEAN = "Street cleaning"

API_TO_SERVICE = {
    "UMIDO": WASTE_TYPE_ORGANIC,
    "INDIFFERENZIATO": WASTE_TYPE_NON_RECYCLABLE,
    "PLASTICA, LATTINE E TETRAPAK": WASTE_TYPE_PLASTIC,
    "CARTA E CARTONE": WASTE_TYPE_PAPER,
    "VETRO": WASTE_TYPE_GLASS,
    "Pulizia Meccanizzata": STREET_CLEAN,
}
