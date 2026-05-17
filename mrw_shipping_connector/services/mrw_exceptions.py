class MRWError(Exception):
    """Base exception for MRW connector errors."""


class MRWConnectionError(MRWError):
    """Raised when the MRW SOAP client cannot connect."""


class MRWAuthenticationError(MRWError):
    """Raised when MRW rejects credentials."""


class MRWRemoteError(MRWError):
    """Raised when MRW returns a business error."""


class MRWLabelError(MRWError):
    """Raised when a label response cannot be processed."""


class MRWUnsupportedOperationError(MRWError):
    """Raised when an MRW operation has no confirmed API contract."""

