"""Compatibility wrapper for shared application state."""

try:
    from .core.state import AppRuntime, T_GLOBALS, TranscriptionGlobals, create_app_runtime
except ImportError:
    from core.state import AppRuntime, T_GLOBALS, TranscriptionGlobals, create_app_runtime

__all__ = ["AppRuntime", "T_GLOBALS", "TranscriptionGlobals", "create_app_runtime"]
