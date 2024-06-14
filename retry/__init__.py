__all__ = ['retry', 'retry_call', 'retry_call_async']
__version__ = "1.0.7"

import logging

from .api import retry, retry_call, retry_call_async


# Set default logging handler to avoid "No handler found" warnings.
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
