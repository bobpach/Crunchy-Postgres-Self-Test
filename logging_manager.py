"""Contains the LoggingManager class
"""
import logging
import os
import sys


class LoggingManager():
    """Provides a logger that logs to a file, stderr and stdout
    """

    # initialize static logger
    def __init__(self):
        if not hasattr(LoggingManager, 'logger'):
            LoggingManager.logger = self.get_logger()

    def get_logger(self):
        """ Creates logger and handlers

        Returns:
            logging.logger: A logger initialized with 3 handlers:
            stderr, stdout and file handler
        """
        # create logger
        _logger = logging.getLogger('self_test')
        log_level = self.get_log_level()
        _logger.setLevel(log_level)

        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - \
          %(levelname)s - %(message)s')

        # create file handler
        log_path = os.getenv('LOG_PATH') + "/self_test.log"
        fh = logging.FileHandler(log_path)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        _logger.addHandler(fh)

        # create a stream handler for stdout
        sh = logging.StreamHandler(stream=sys.stdout)
        sh.setLevel(log_level)
        sh.setFormatter(formatter)
        _logger.addHandler(sh)

        # create a stream handler for stderr
        # only logging errors and above to this handler
        eh = logging.StreamHandler(stream=sys.stderr)
        eh.setLevel(logging.ERROR)
        eh.setFormatter(formatter)
        _logger.addHandler(eh)

        return _logger

    def remove_handlers(self, logger):
        """ Removes handlers from logger

        Args:
            logger (logging.logger): The logger instance that is being closed
        """
        for handler in logger.handlers:
            handler.close()
            logger.removeFilter(handler)

    def get_log_level(self):
        """ Sets logging level enum based on configured value

        Returns:
            int: logger.logging logging level enum member
        """
        config_log_level = os.getenv('LOG_LEVEL').lower()
        match config_log_level:
            case "debug":
                return logging.DEBUG
            case "info":
                return logging.INFO
            case "warning":
                return logging.WARNING
            case "error":
                return logging.ERROR
            case "critical":
                return logging.CRITICAL

        # return default of info if value is not a match
        return logging.INFO
