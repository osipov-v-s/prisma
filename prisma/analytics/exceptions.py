"""Domain-specific errors raised by the analytics boundary."""


class AnalyticsError(Exception):
    """Base class for analytics errors."""


class AnalyticsValidationError(AnalyticsError, ValueError):
    """Input data cannot represent a reproducible pairwise session."""

