# -*- coding: utf-8 -*-
"""Exceptions for Silea waste pickup."""


class SileaWpError(Exception):
    """Generic Silea waste pickup exception."""

    pass


class SileaWpConnectionError(SileaWpError):
    """Silea waste pickup connection exception."""

    pass


class SileaWpAddressError(SileaWpError):
    """Silea waste pickup unknown address exception."""

    pass