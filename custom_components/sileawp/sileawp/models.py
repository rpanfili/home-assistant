# -*- coding: utf-8 -*-
"""Pydantic models for Silea waste pickup API responses."""
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, RootModel


class ServiceDate(BaseModel):
    """Model for the date object in the API response."""

    date: str
    timezone_type: int
    timezone: str


class WasteService(BaseModel):
    """Model for individual waste collection service."""

    service: str
    hours: str
    notes: str
    type: str


class PickupDay(BaseModel):
    """Model for a single day's pickup schedule."""

    date_formatted: str
    format: str = Field(..., description="ISO format date string")
    date: ServiceDate
    services: List[WasteService]

    @property
    def pickup_date(self) -> datetime:
        """Return the pickup date as a datetime object."""
        return datetime.fromisoformat(self.date.date)


class CalendarResponse(RootModel[List[PickupDay]]):
    """Model for the complete calendar API response.
    
    This is a root model that wraps a list of PickupDay objects.
    Usage: CalendarResponse(data) or CalendarResponse.model_validate(data)
    """

    root: List[PickupDay]

    def __iter__(self):
        """Allow iteration over pickup days."""
        return iter(self.root)

    def __getitem__(self, item):
        """Allow indexing of pickup days."""
        return self.root[item]

    def __len__(self):
        """Return the number of pickup days."""
        return len(self.root)
