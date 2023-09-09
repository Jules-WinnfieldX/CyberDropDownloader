

from typing import Tuple, List, Dict

from rich.console import Group
from rich.progress import Progress, BarColumn, TaskID


class DownloadStatsProgress:
    """Class that keeps track of download failures and reasons"""

    def __init__(self):
        self.progress = Progress("[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "{task.completed} of {task.total} Files Completed")
        self.progress_group = Group(self.progress)

        self.failure_types: Dict[str, TaskID] = {}
        self.failed_files_task_id = self.progress.add_task("[red]Failed", total=0)
        self.failed_files = 0

    async def get_progress(self) -> Group:
        return self.progress_group

    async def update_total(self, total: int) -> None:
        for key in self.failure_types.keys():
            self.progress.update(self.failure_types[key], total=total)

    async def add_failure(self, failure_type: str) -> None:
        if failure_type in self.failure_types:
            self.progress.advance(self.failure_types[failure_type], 1)
        else:
            self.failure_types[failure_type] = self.progress.add_task(failure_type, total=1)

        self.progress.advance(self.failed_files_task_id, 1)
        self.failed_files += 1

    async def return_totals(self) -> Dict:
        failures = {}
        for key, value in self.failure_types.items():
            failures[key] = self.progress.tasks[value].completed
        return failures


class ScrapeStatsProgress:
    """Class that keeps track of scraping failures and reasons"""

    def __init__(self):
        self.progress = Progress("[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "{task.completed} of {task.total} Files Completed")
        self.progress_group = Group(self.progress)

        self.failure_types: Dict[str, TaskID] = {}
        self.failed_files_task_id = self.progress.add_task("[red]Failed", total=0)
        self.failed_files = 0

    async def get_progress(self) -> Group:
        return self.progress_group

    async def update_total(self, total: int) -> None:
        for key in self.failure_types.keys():
            self.progress.update(self.failure_types[key], total=total)

    async def add_failure(self, failure_type: str) -> None:
        if failure_type in self.failure_types:
            self.progress.advance(self.failure_types[failure_type], 1)
        else:
            self.failure_types[failure_type] = self.progress.add_task(failure_type, total=1)

        self.progress.advance(self.failed_files_task_id, 1)
        self.failed_files += 1

    async def return_totals(self) -> Dict:
        failures = {}
        for key, value in self.failure_types.items():
            failures[key] = self.progress.tasks[value].completed
        return failures
