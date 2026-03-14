"""Compatibility wrapper for shared application state."""

try:
    from .core.state import T_GLOBALS, TranscriptionGlobals
except ImportError:
    from core.state import T_GLOBALS, TranscriptionGlobals

__all__ = ["T_GLOBALS", "TranscriptionGlobals"]
