"""Compatibility wrapper for CLI modules."""

try:
    from .cli.arguments import create_args, update_args_config
    from .cli.batch import handle_batch_tasks
except ImportError:
    from cli.arguments import create_args, update_args_config
    from cli.batch import handle_batch_tasks


def handle_args_batch_tasks(args, _global_vars=None, config=None):
    """Backward-compatible wrapper around the CLI batch task handler."""
    return handle_batch_tasks(args=args, config=config)

__all__ = ["create_args", "handle_args_batch_tasks", "update_args_config"]
