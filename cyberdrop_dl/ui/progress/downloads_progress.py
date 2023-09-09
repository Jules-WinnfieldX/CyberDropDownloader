from typing import Tuple

from rich.console import Group
from rich.progress import Progress, BarColumn


class DownloadsProgress:
    """Class that keeps track of completed, skipped and failed files"""

    def __init__(self):
        self.progress = Progress("[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "{task.completed} of {task.total} Files Completed")
        self.progress_group = Group(self.progress)

        self.completed_files_task_id = self.progress.add_task("[green]Completed", total=0)
        self.completed_files = 0
        self.previously_completed_files_task_id = self.progress.add_task("[Yellow]Previously Downloaded", total=0)
        self.previously_completed_files = 0
        self.skipped_files_task_id = self.progress.add_task("[yellow]Skipped By Configuration", total=0)
        self.skipped_files = 0
        self.failed_files_task_id = self.progress.add_task("[red]Failed", total=0)
        self.failed_files = 0

    async def get_progress(self) -> Group:
        return self.progress_group

    async def update_total(self, total_files: int) -> None:
        self.progress.update(self.completed_files_task_id, total=total_files)
        self.progress.update(self.previously_completed_files_task_id, total=total_files)
        self.progress.update(self.skipped_files_task_id, total=total_files)
        self.progress.update(self.failed_files_task_id, total=total_files)

    async def add_completed(self) -> None:
        self.progress.advance(self.completed_files_task_id, 1)
        self.completed_files += 1

    async def add_previously_completed(self) -> None:
        self.progress.advance(self.previously_completed_files_task_id, 1)
        self.previously_completed_files += 1

    async def add_skipped(self) -> None:
        self.progress.advance(self.skipped_files_task_id, 1)
        self.skipped_files += 1

    async def add_failed(self) -> None:
        self.progress.advance(self.failed_files_task_id, 1)
        self.failed_files += 1

    async def return_totals(self) -> Tuple[int, int, int, int]:
        return self.completed_files, self.previously_completed_files, self.skipped_files, self.failed_files

    async def hide(self) -> None:
        self.progress.update(self.completed_files_task_id, visible=False)
        self.progress.update(self.previously_completed_files_task_id, visible=False)
        self.progress.update(self.skipped_files_task_id, visible=False)
        self.progress.update(self.failed_files_task_id, visible=False)
