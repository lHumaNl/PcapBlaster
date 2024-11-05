import datetime
import logging
import os.path


class Logger:
    __CURRENT_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
    __FORMAT_STR = '[%(asctime)s] %(levelname)s | module: %(module)s | funcName: %(funcName)s | %(message)s'
    __DATEFORMAT = '%Y-%m-%d %H:%M:%S'
    __ENCODING = 'utf-8'
    __FORMATTER = logging.Formatter(__FORMAT_STR, __DATEFORMAT)

    @staticmethod
    def init_logger():
        """
        Set up logging configuration.
        """

        logging.basicConfig(
            level=logging.INFO,
            format=Logger.__FORMAT_STR,
            datefmt=Logger.__DATEFORMAT,
        )

        logger = logging.getLogger()

        os.makedirs('log', exist_ok=True)
        error_log_path = os.path.join('log', f'pcap_blaster_errors_{Logger.__CURRENT_DATE}.log')
        log_path = os.path.join('log', f'pcap_blaster_full_{Logger.__CURRENT_DATE}.log')

        error_file_handler = logging.FileHandler(error_log_path, encoding=Logger.__ENCODING)
        full_file_handler = logging.FileHandler(log_path, encoding=Logger.__ENCODING)

        error_file_handler.setLevel(logging.WARNING)
        full_file_handler.setLevel(logging.INFO)

        error_file_handler.setFormatter(Logger.__FORMATTER)
        full_file_handler.setFormatter(Logger.__FORMATTER)

        logger.addHandler(error_file_handler)
        logger.addHandler(full_file_handler)

    @staticmethod
    def append_logger(test_folder: str):
        logger = logging.getLogger()

        error_log_path = os.path.join(test_folder, f'pcap_blaster_errors.log')
        log_path = os.path.join(test_folder, f'pcap_blaster_full.log')

        error_file_handler = logging.FileHandler(error_log_path, encoding=Logger.__ENCODING)
        full_file_handler = logging.FileHandler(log_path, encoding=Logger.__ENCODING)

        error_file_handler.setLevel(logging.WARNING)
        full_file_handler.setLevel(logging.INFO)

        error_file_handler.setFormatter(Logger.__FORMATTER)
        full_file_handler.setFormatter(Logger.__FORMATTER)

        logger.addHandler(error_file_handler)
        logger.addHandler(full_file_handler)
