from typing import Dict

from rich.console import Group
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TaskID


class DownloadStatsProgress:
    """Class that keeps track of download failures and reasons"""

    def __init__(self):
        self.progress = Progress("[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "{task.completed} of {task.total} Files")
        self.progress_group = Group(self.progress)

        self.failure_types: Dict[str, TaskID] = {}
        self.failed_files = 0

    async def get_progress(self) -> Panel:
        """Returns the progress bar"""
        return Panel(self.progress_group, title="Download Failures", border_style="green", padding=(1, 1))

    async def update_total(self, total: int) -> None:
        """Updates the total number of files to be downloaded"""
        for key in self.failure_types:
            self.progress.update(self.failure_types[key], total=total)

    async def add_failure(self, failure_type: [str, int]) -> None:
        """Adds a failed file to the progress bar"""
        self.failed_files += 1
        if isinstance(failure_type, int):
            failure_type = str(failure_type) + " HTTP Status"

        if failure_type in self.failure_types:
            self.progress.advance(self.failure_types[failure_type], 1)
        else:
            self.failure_types[failure_type] = self.progress.add_task(failure_type, total=self.failed_files, completed=1)
        await self.update_total(self.failed_files)

    async def return_totals(self) -> Dict:
        """Returns the total number of failed files"""
        failures = {}
        for key, value in self.failure_types.items():
            failures[key] = self.progress.tasks[value].completed
        return dict(sorted(failures.items()))


class ScrapeStatsProgress:
    """Class that keeps track of scraping failures and reasons"""

    def __init__(self):
        self.progress = Progress("[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "{task.completed} of {task.total} Files")
        self.progress_group = Group(self.progress)

        self.failure_types: Dict[str, TaskID] = {}
        self.failed_files = 0

    async def get_progress(self) -> Panel:
        """Returns the progress bar"""
        return Panel(self.progress_group, title="Scrape Failures", border_style="green", padding=(1, 1))

    async def update_total(self, total: int) -> None:
        """Updates the total number of sites to be scraped"""
        for key in self.failure_types:
            self.progress.update(self.failure_types[key], total=total)

    async def add_failure(self, failure_type: [str, int]) -> None:
        """Adds a failed site to the progress bar"""
        self.failed_files += 1
        if isinstance(failure_type, int):
            failure_type = str(failure_type) + " HTTP Status"

        if failure_type in self.failure_types:
            self.progress.advance(self.failure_types[failure_type], 1)
        else:
            self.failure_types[failure_type] = self.progress.add_task(failure_type, total=self.failed_files, completed=1)
        await self.update_total(self.failed_files)

    async def return_totals(self) -> Dict:
        """Returns the total number of failed sites and reasons"""
        failures = {}
        for key, value in self.failure_types.items():
            failures[key] = self.progress.tasks[value].completed
        return dict(sorted(failures.items()))
