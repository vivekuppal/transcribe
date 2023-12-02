import threading
import queue
import time
from enum import Enum
from tsutils import utilities


class TaskQueueEnum(Enum):
    """Type of tasks that can be put in task queue
    """
    ZIP_TASK = 1


class TaskQueue:

    def __init__(self):
        self.mutex = threading.Lock()
        self.task_list = queue.Queue()

    def add(self, **params):
        with self.mutex:
            self.task_list.put(params)

    def task_exec_thread(self):
        while True:
            # Wait atleast 20s between two tasks
            time.sleep(5)
            queue_item = self.task_list.get()
            try:
                task_type = queue_item['task_type']
                if task_type == TaskQueueEnum.ZIP_TASK:
                    utilities.zip_files_in_folder_with_params(**queue_item)
            except KeyError as ke:
                print('Caught exception executing tasks in task queue.')
                print(f'Mandatory input argument {ke} not found.')
