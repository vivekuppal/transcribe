"""Desktop workflow helpers for background tasks and UI callback sequencing."""

from __future__ import annotations

import threading

from tsutils import app_logging as al

from .services import ConversationInsightsService


logger = al.get_module_logger(al.UI_LOGGER)

SUMMARY_FAILURE_MESSAGE = "Failed to get summary. Please check you have a valid API key."


class DesktopWorkflowService:
    """Run desktop workflows and marshal results back through callbacks."""

    def __init__(
        self,
        runtime,
        insights_service: ConversationInsightsService = None,
        thread_factory=threading.Thread,
    ):
        self.global_vars = runtime
        self.insights_service = insights_service or ConversationInsightsService()
        self.thread_factory = thread_factory

    def start_response_workflow(self, response_generator, on_response, thread_name: str):
        """Start a response workflow unless one is already running."""
        if self.global_vars.update_response_now:
            return False

        response_thread = self.thread_factory(
            target=self.run_response_workflow,
            name=thread_name,
            args=(response_generator, on_response),
        )
        response_thread.daemon = True
        response_thread.start()
        return True

    def run_response_workflow(self, response_generator, on_response):
        """Run response generation and emit the result through a callback."""
        try:
            self.global_vars.update_response_now = True
            response_string = response_generator()
            if self.global_vars.read_response and self.global_vars.audio_player_var is not None:
                self.global_vars.audio_player_var.speech_text_available.set()
            if response_string:
                on_response(response_string)
        except Exception as exception:
            logger.error(f"Error in threaded response: {exception}")
        finally:
            self.global_vars.update_response_now = False

    def start_summary_workflow(self, summarize_fn, on_loading, on_close, on_message, thread_name: str):
        """Start the summary workflow in a background thread."""
        summary_thread = self.thread_factory(
            target=self.run_summary_workflow,
            name=thread_name,
            args=(summarize_fn, on_loading, on_close, on_message),
        )
        summary_thread.daemon = True
        summary_thread.start()
        return True

    def run_summary_workflow(self, summarize_fn, on_loading, on_close, on_message):
        """Run summary generation and route status updates through callbacks."""
        try:
            on_loading("Summary", "Creating a summary")
            summary = summarize_fn()
            on_close()
            if summary is None:
                on_message("Summary", SUMMARY_FAILURE_MESSAGE)
                return

            on_message("Summary", summary)
        except Exception as exception:
            logger.error(f"Error in summarize_threaded: {exception}")

    def start_word_cloud_workflow(self, words_provider, on_close, on_word_cloud, thread_name: str):
        """Start the word cloud workflow in a background thread."""
        word_cloud_thread = self.thread_factory(
            target=self.run_word_cloud_workflow,
            name=thread_name,
            args=(words_provider, on_close, on_word_cloud),
        )
        word_cloud_thread.daemon = True
        word_cloud_thread.start()
        return True

    def run_word_cloud_workflow(self, words_provider, on_close, on_word_cloud):
        """Run word cloud generation and emit the rendered cloud through a callback."""
        try:
            on_close()
            words = words_provider()
            word_cloud = self.insights_service.build_word_cloud(words)
            on_word_cloud("Word Cloud", word_cloud)
        except Exception as exception:
            logger.error(f"Error in word_cloud_threaded: {exception}")
