import queue
import logging
from logging import handlers
import logging.config
import constants


root_logger: logging.Logger = logging.getLogger(name=constants.LOG_NAME)
AUDIO_PLAYER_LOGGER: str = 'audio_player'
TRANSCRIBER_LOGGER: str = 'transcriber'
GPT_RESPONDER_LOGGER: str = 'gpt_responder'
AUDIO_RECORDER_LOGGER: str = 'audio_recorder'
UI_LOGGER: str = 'ui'


def initiate_log(config: dict) -> handlers.QueueListener:
    log_file_name = config['General']['log_file']
    setup_logging(log_file_name)
    que = queue.Queue(-1)
    queue_handler = handlers.QueueHandler(que)
    handler = logging.FileHandler(log_file_name, mode='w', encoding='utf-8')
    log_listener = handlers.QueueListener(que, handler)
    root_logger.setLevel(level=logging.INFO)
    root_logger.addHandler(queue_handler)
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(threadName)s: %(message)s')
    handler.setFormatter(log_formatter)
    log_listener.start()
    root_logger.info('Logging started for application!')
    return log_listener


def get_logger() -> logging.Logger:
    """Get root logger"""
    return root_logger


def get_module_logger(module_name) -> logging.Logger:
    """Get module logger"""
    return logging.getLogger(module_name)


def setup_logging(log_file_name: str):
    """Initial config for setting up loggers"""
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
            # '': {
            #     'handlers': ['file'],  # 'console', 'file'
            #     'level': 'DEBUG',
            #     'propagate': False,
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
            UI_LOGGER:  {
                'handlers': ['file'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    logging.config.dictConfig(logging_config)
