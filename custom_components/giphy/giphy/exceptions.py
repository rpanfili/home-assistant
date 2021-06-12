# -*- coding: utf-8 -*-
"""Exceptions for Giphy."""


class GiphyError(Exception):
    """Generic Giphy exception."""

    pass


class GiphyConnectionError(GiphyError):
    """Giphy connection exception."""

    pass


class GiphyAddressError(GiphyError):
    """Giphy unknown address exception."""

    pass