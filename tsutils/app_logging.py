import queue
import logging
from logging import handlers
import logging.config
import constants
from tsutils import utilities

root_logger: logging.Logger = logging.getLogger(name=constants.LOG_NAME)
AUDIO_PLAYER_LOGGER: str = 'audio_player'
TRANSCRIBER_LOGGER: str = 'transcriber'
GPT_RESPONDER_LOGGER: str = 'gpt_responder'
AUDIO_RECORDER_LOGGER: str = 'audio_recorder'
UI_LOGGER: str = 'ui'


def initiate_log(config: dict) -> handlers.QueueListener:
    """
    Initiates logging for the application.

    Args:
        config (dict): Configuration dictionary containing logging settings.

    Returns:
        handlers.QueueListener: The logging queue listener.
    """
    data_dir = utilities.get_data_path(app_name='Transcribe')
    log_file_name = f"{data_dir}/{config['General']['log_file']}"
    setup_logging(log_file_name)
    que = queue.Queue(-1)
    queue_handler = handlers.QueueHandler(que)
    handler = logging.FileHandler(log_file_name, mode='w', encoding='utf-8')
    log_listener = handlers.QueueListener(que, handler)
    root_logger.setLevel(level=logging.INFO)
    root_logger.addHandler(queue_handler)
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(threadName)s: %(message)s')
    handler.setFormatter(log_formatter)

    try:
        log_listener.start()
        root_logger.info('Logging started for application!')
    except Exception as e:
        root_logger.error(f"Failed to start log listener: {e}")

    return log_listener


def get_logger() -> logging.Logger:
    """
    Returns the root logger.

    Returns:
        logging.Logger: The root logger.
    """
    return root_logger


def get_module_logger(module_name: str) -> logging.Logger:
    """
    Returns a logger for the specified module.

    Args:
        module_name (str): The name of the module.

    Returns:
        logging.Logger: The logger for the specified module.
    """
    return logging.getLogger(module_name)


def setup_logging(log_file_name: str):
    """
    Initial configuration for setting up loggers.

    Args:
        log_file_name (str): The name of the log file.
    """
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': log_file_name,
                'formatter': 'standard',
            },
        },
        'loggers': {
            # Settings for default log handler propagated to all handlers
            # '': {
            #     'handlers': ['file'],  # 'console', 'file'
            #     'level': 'DEBUG',
            #     'propagate': True,
            # },
            AUDIO_PLAYER_LOGGER: {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False,
            },
            AUDIO_RECORDER_LOGGER: {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False,
            },
            TRANSCRIBER_LOGGER: {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False,
            },
            GPT_RESPONDER_LOGGER: {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False,
            },
            UI_LOGGER: {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    logging.config.dictConfig(logging_config)
