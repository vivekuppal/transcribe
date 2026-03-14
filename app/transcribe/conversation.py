"""Compatibility wrapper for the core conversation model."""

try:
    from .core.conversation import Conversation
except ImportError:
    from core.conversation import Conversation

__all__ = ["Conversation"]
