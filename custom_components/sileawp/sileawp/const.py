# -*- coding: utf-8 -*-
"""Silea waste pickup constants."""

API_HOST = "www.sileaspa.it"
API_BASE_URI = "/api/servizi/"
API_TOKEN = "9101D451-E505-4461-A8E8-0AC205FC8703"

WASTE_TYPE_NON_RECYCLABLE = "Non-recyclable"
WASTE_TYPE_ORGANIC = "Organic"
WASTE_TYPE_PAPER = "Paper"
WASTE_TYPE_PLASTIC = "Plastic"
WASTE_TYPE_GLASS = "Glass"
STREET_CLEAN = "Street cleaning"

API_TO_SERVICE = {
    "raccolta UMIDO": WASTE_TYPE_ORGANIC,
    "raccolta SECCO": WASTE_TYPE_NON_RECYCLABLE,
    "raccolta RICICLABILE": WASTE_TYPE_PLASTIC,
    "raccolta CARTA CARTONE": WASTE_TYPE_PAPER,
    "raccolta VETRO": WASTE_TYPE_GLASS,
    "Pulizia Meccanizzata": STREET_CLEAN
}