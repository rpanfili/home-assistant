# -*- coding: utf-8 -*-
"""Silea waste pickup constants."""
from enum import StrEnum

API_HOST = "www.sileaspa.it"
API_BASE_URI = "/wp-admin/admin-ajax.php"


class ServiceType(StrEnum):
    """Normalized waste collection service types."""
    
    NON_RECYCLABLE = "Non-recyclable"
    ORGANIC = "Organic"
    PAPER = "Paper"
    PLASTIC = "Plastic"
    GLASS = "Glass"
    STREET_CLEAN = "Street cleaning"


class ApiServiceType(StrEnum):
    """Raw service type names from the Silea API."""
    
    UMIDO = "UMIDO"
    INDIFFERENZIATO = "INDIFFERENZIATO"
    PLASTICA = "PLASTICA, LATTINE E TETRAPAK"
    CARTA = "CARTA E CARTONE"
    VETRO = "VETRO"
    PULIZIA = "Pulizia Meccanizzata"


# Backward compatibility - deprecated, use ServiceType enum instead
WASTE_TYPE_NON_RECYCLABLE = ServiceType.NON_RECYCLABLE
WASTE_TYPE_ORGANIC = ServiceType.ORGANIC
WASTE_TYPE_PAPER = ServiceType.PAPER
WASTE_TYPE_PLASTIC = ServiceType.PLASTIC
WASTE_TYPE_GLASS = ServiceType.GLASS
STREET_CLEAN = ServiceType.STREET_CLEAN

# Mapping from API service names to normalized service types
API_TO_SERVICE = {
    ApiServiceType.UMIDO: ServiceType.ORGANIC,
    ApiServiceType.INDIFFERENZIATO: ServiceType.NON_RECYCLABLE,
    ApiServiceType.PLASTICA: ServiceType.PLASTIC,
    ApiServiceType.CARTA: ServiceType.PAPER,
    ApiServiceType.VETRO: ServiceType.GLASS,
    ApiServiceType.PULIZIA: ServiceType.STREET_CLEAN,
}
