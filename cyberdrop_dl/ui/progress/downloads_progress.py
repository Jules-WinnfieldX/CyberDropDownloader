from typing import Tuple, TYPE_CHECKING

from rich.console import Group
from rich.panel import Panel
from rich.progress import Progress, BarColumn

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class DownloadsProgress:
    """Class that keeps track of completed, skipped and failed files"""

    def __init__(self, manager: 'Manager'):
        self.manager = manager
        self.progress = Progress("[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "{task.completed} of {task.total} Files")
        self.progress_group = Group(self.progress)

        self.total_files = 0
        self.completed_files_task_id = self.progress.add_task("[green]Completed", total=0)
        self.completed_files = 0
        self.previously_completed_files_task_id = self.progress.add_task("[yellow]Previously Downloaded", total=0)
        self.previously_completed_files = 0
        self.skipped_files_task_id = self.progress.add_task("[yellow]Skipped By Configuration", total=0)
        self.skipped_files = 0
        self.failed_files_task_id = self.progress.add_task("[red]Failed", total=0)
        self.failed_files = 0

    async def get_progress(self) -> Panel:
        """Returns the progress bar"""
        return Panel(self.progress_group, title=f"Config: {self.manager.config_manager.loaded_config}", border_style="green", padding=(1, 1))

    async def update_total(self) -> None:
        """Updates the total number of files to be downloaded"""
        self.total_files = self.total_files + 1
        self.progress.update(self.completed_files_task_id, total=self.total_files)
        self.progress.update(self.previously_completed_files_task_id, total=self.total_files)
        self.progress.update(self.skipped_files_task_id, total=self.total_files)
        self.progress.update(self.failed_files_task_id, total=self.total_files)

    async def add_completed(self) -> None:
        """Adds a completed file to the progress bar"""
        self.progress.advance(self.completed_files_task_id, 1)
        self.completed_files += 1

    async def add_previously_completed(self, increase_total: bool = True) -> None:
        """Adds a previously completed file to the progress bar"""
        if increase_total:
            await self.update_total()
        self.previously_completed_files += 1
        self.progress.advance(self.previously_completed_files_task_id, 1)

    async def add_skipped(self) -> None:
        """Adds a skipped file to the progress bar"""
        self.progress.advance(self.skipped_files_task_id, 1)
        self.skipped_files += 1

    async def add_failed(self) -> None:
        """Adds a failed file to the progress bar"""
        self.progress.advance(self.failed_files_task_id, 1)
        self.failed_files += 1

    async def return_totals(self) -> Tuple[int, int, int, int]:
        """Returns the total number of completed, previously completed, skipped and failed files"""
        return self.completed_files, self.previously_completed_files, self.skipped_files, self.failed_files
