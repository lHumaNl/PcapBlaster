import logging
import sys

from models.config import Config
from utils.args_parser import ArgsParser
from utils.logger import Logger
from utils.tcpreplay_runner import TcpreplayRunner
from utils.report_generator import ReportGenerator
from utils.visualizer import Visualizer


def main():
    """
    Main function to run the test runner.
    """
    Logger.init_logger()
    args = ArgsParser()

    try:
        config = Config(args.config, args.load, args.test_type, args.test_id, args.test_tag, args.sudo_password,
                        args.test_folder)

        if args.test_folder is None:
            runner = TcpreplayRunner(config)
            runner.run()

        report_generator = ReportGenerator(config=config)
        report_generator.generate_report()

        Visualizer.visualize(report_generator.df_stage_combined, report_generator.df_stability_combined,
                             config.load_config.test_folder)
    except Exception as e:
        logging.error(f"An error occurred: {e.with_traceback()}")
        sys.exit(1)


if __name__ == '__main__':
    main()
