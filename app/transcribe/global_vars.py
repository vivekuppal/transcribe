"""Compatibility wrapper for shared application state."""

from .core.state import AppRuntime, T_GLOBALS, TranscriptionGlobals, create_app_runtime

__all__ = ["AppRuntime", "T_GLOBALS", "TranscriptionGlobals", "create_app_runtime"]
