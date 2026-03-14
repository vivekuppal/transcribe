"""Desktop application runtime composition."""

from .bindings import DesktopCommandBinder
from .controller import DesktopController
from .presenter import DesktopPresenter
from .runtime import (
    initialize_desktop_runtime,
    initiate_app_threads,
    initiate_db,
    shutdown,
    start_audio_capture,
)
from .services import (
    ActionLogService,
    BrowserService,
    ConversationInsightsService,
    SettingsService,
    TranscriptIOService,
)
from .view import DesktopViewBuilder
from .workflows import DesktopWorkflowService

__all__ = [
    "ActionLogService",
    "BrowserService",
    "ConversationInsightsService",
    "DesktopCommandBinder",
    "DesktopController",
    "DesktopPresenter",
    "DesktopViewBuilder",
    "DesktopWorkflowService",
    "SettingsService",
    "TranscriptIOService",
    "initialize_desktop_runtime",
    "initiate_app_threads",
    "initiate_db",
    "shutdown",
    "start_audio_capture",
]
