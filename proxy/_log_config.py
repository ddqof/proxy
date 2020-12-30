from pathlib import PurePath

LOGFILE_PATH = PurePath(__file__).parent / "log.log"

LOGGING_CONFIG = {
    "version": 1,
    "loggers": {
        "proxy.proxy": {
            "level": "INFO",
            "handlers": [
                "info_file_handler",
                "debug_console_handler",
            ],
            "propagate": False
        }
    },
    "handlers": {
        "debug_console_handler": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "debug_format"
        },
        "info_file_handler": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "info_format",
            "filename": LOGFILE_PATH,
        },
        "warning_console_handler": {
            "level": "WARNING",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "debug_format"
        },
    },
    "formatters": {
        "info_format": {
            "format": "[{asctime}] [{levelname}] {message}",
            "style": "{",
            "datefmt": "%d-%b-%Y:%H:%M:%S"
        },
        "debug_format": {
            "format": "[{asctime}] [{levelname}] {message} ({funcName}:{lineno})",
            "style": "{",
            "datefmt": "%d-%b-%Y:%H:%M:%S",
        }
    }
}
