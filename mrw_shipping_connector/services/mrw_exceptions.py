class MRWError(Exception):
    """Base exception for MRW connector errors."""


class MRWConnectionError(MRWError):
    """Raised when the MRW SOAP client cannot connect."""


class MRWTrackingResponseError(MRWConnectionError):
    """Raised when a tracking response must be retained for diagnostics."""

    def __init__(self, message, request_raw=False, response_raw=False):
        super().__init__(message)
        self.request_raw = request_raw
        self.response_raw = response_raw


class MRWAuthenticationError(MRWError):
    """Raised when MRW rejects credentials."""


class MRWRemoteError(MRWError):
    """Raised when MRW returns a business error."""


class MRWLabelError(MRWError):
    """Raised when a label response cannot be processed."""


class MRWUnsupportedOperationError(MRWError):
    """Raised when an MRW operation has no confirmed API contract."""
