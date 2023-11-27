import datetime
import time
import app_logging as al


# pylint: disable=logging-fstring-interpolation
root_logger = al.get_logger()


class Duration:
    """A class to measure duration of an action.
    Example usage of the class is
        with Duration('Test Operation') as measure:
            print('Performing Test operation')
            ... Do the necessary operations
            time.sleep(2)

    When the with block ends, it will print out the duration
    of the operation in the following format
        Performing Test operation
        Duration(hh:mm::ss.ms) of Test Operation 0:00:02.000826
    """

    def __init__(self, name: str = 'undefined',
                 log: bool = True,
                 screen: bool = False):
        self.start: datetime.datetime = None
        self.end: datetime.datetime = None
        self.operation_name = name
        self.log = log
        self.screen = screen

    def __enter__(self):
        """Records the start time of an operation
        """
        self.start = datetime.datetime.now()

    def __exit__(self, exception_type, exception_value, traceback):
        """Records the end time of an operation
        Prints the duration between start and end of an operation
        """
        self.end = datetime.datetime.now()
        if self.log:
            root_logger.info(f'Duration(hh:mm:ss.ms) of {self.operation_name} {self.end - self.start}')
        if self.screen:
            print(f'Duration(hh:mm:ss.ms) of {self.operation_name} {self.end - self.start}')


if __name__ == "__main__":
    print('Start executing main...')
    with Duration('Test Operation') as measure:
        time.sleep(2)
    print('Done executing main...')
