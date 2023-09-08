from __future__ import annotations

import contextlib
from typing import Dict, List, Optional, Tuple

from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


def adjust_title(s: str, length: int = 40, placeholder: str = "...") -> str:
    """Collapse and truncate or pad the given string to fit in the given length"""
    return f"{s[:length - len(placeholder)]}{placeholder}" if len(s) >= length else s.ljust(length)


class Progressions:
    def __init__(self):
        self.overall_file_progress = Progress("[progress.description]{task.description}",
                                              BarColumn(bar_width=None),
                                              "[progress.percentage]{task.percentage:>3.2f}%",
                                              "{task.completed} of {task.total} Files Completed")

        self.file_progress = Progress(SpinnerColumn(),
                                      "[progress.description]{task.description}",
                                      BarColumn(bar_width=None),
                                      "[progress.percentage]{task.percentage:>3.2f}%",
                                      "━",
                                      DownloadColumn(),
                                      "━",
                                      TransferSpeedColumn(),
                                      "━",
                                      TimeRemainingColumn())
        self.file_progress_overflow = Progress("[progress.description]{task.description}")

    async def get_overall_progress(self) -> Group:
        return Group(self.overall_file_progress)

    async def get_file_progress(self) -> Group:
        return Group(self.file_progress, self.file_progress_overflow)


class OverallFileProgress:
    """Class that keeps track of completed, skipped and failed files"""

    def __init__(self, total_files: int, overall_file_progress: Progress):
        self.overall_file_progress = overall_file_progress

        self.completed_files_task_id = overall_file_progress.add_task("[green]Completed", total=total_files)
        self.completed_files = 0
        self.previously_completed_files_task_id = overall_file_progress.add_task("[green]Previously Completed", total=total_files)
        self.previously_completed_files = 0
        self.skipped_files_task_id = overall_file_progress.add_task("[yellow]Skipped", total=total_files)
        self.skipped_files = 0
        self.failed_files_task_id = overall_file_progress.add_task("[red]Failed", total=total_files)
        self.failed_files = 0

    async def update_total(self, total_files: int) -> None:
        self.overall_file_progress.update(self.completed_files_task_id, total=total_files)
        self.overall_file_progress.update(self.previously_completed_files_task_id, total=total_files)
        self.overall_file_progress.update(self.skipped_files_task_id, total=total_files)
        self.overall_file_progress.update(self.failed_files_task_id, total=total_files)

    async def add_completed(self) -> None:
        self.overall_file_progress.advance(self.completed_files_task_id, 1)
        self.completed_files += 1

    async def add_previously_completed(self) -> None:
        self.overall_file_progress.advance(self.previously_completed_files_task_id, 1)
        self.previously_completed_files += 1

    async def add_skipped(self) -> None:
        self.overall_file_progress.advance(self.skipped_files_task_id, 1)
        self.skipped_files += 1

    async def add_failed(self) -> None:
        self.overall_file_progress.advance(self.failed_files_task_id, 1)
        self.failed_files += 1

    async def return_totals(self) -> Tuple[int, int, int, int]:
        return self.completed_files, self.previously_completed_files, self.skipped_files, self.failed_files

    async def hide(self) -> None:
        self.overall_file_progress.update(self.completed_files_task_id, visible=False)
        self.overall_file_progress.update(self.previously_completed_files_task_id, visible=False)
        self.overall_file_progress.update(self.skipped_files_task_id, visible=False)
        self.overall_file_progress.update(self.failed_files_task_id, visible=False)


class FileProgress:
    def __init__(self, progressions: Progressions, visible_tasks_limit: int):
        self.progress = progressions.file_progress
        self.overflow = progressions.file_progress_overflow

        self.color = "plum3"
        self.type_str = "Files"
        self.progress_str = "[{color}]{description}"
        self.overflow_str = "[{color}]... And {number} Other {type_str}"
        self.overflow_task_id = self.overflow.add_task(self.overflow_str.format(color=self.color, number=0, type_str=self.type_str), visible=False)

        self.locked = False

        self.visible_tasks: List[TaskID] = []
        self.invisible_tasks: List[TaskID] = []
        self.completed_tasks: List[TaskID] = []
        self.uninitiated_tasks: List[TaskID] = []
        self.tasks_visibility_limit = visible_tasks_limit

    async def redraw(self):
        while len(self.visible_tasks) > self.tasks_visibility_limit:
            task_id = self.visible_tasks.pop(0)
            self.invisible_tasks.append(task_id)
            self.progress.update(task_id, visible=False)
        while len(self.invisible_tasks) > 0 and len(self.visible_tasks) < self.tasks_visibility_limit:
            task_id = self.invisible_tasks.pop(0)
            self.visible_tasks.append(task_id)
            self.progress.update(task_id, visible=True)
        if len(self.invisible_tasks) > 0:
            self.overflow.update(self.overflow_task_id, description=self.overflow_str.format(color=self.color, number=len(self.invisible_tasks), type_str=self.type_str), visible=True)
        else:
            self.overflow.update(self.overflow_task_id, visible=False)

    async def add_task(self, file: str, expected_size: Optional[int]) -> TaskID:
        description = file.split('/')[-1]
        description = description.encode("ascii", "ignore").decode().strip()
        description = adjust_title(description)

        if len(self.visible_tasks) >= self.tasks_visibility_limit:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=description), total=expected_size, visible=False)
            self.invisible_tasks.append(task_id)
        else:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=description), total=expected_size)
            self.visible_tasks.append(task_id)
        return task_id

    async def remove_file(self, task_id: TaskID) -> None:
        if task_id in self.visible_tasks:
            self.visible_tasks.remove(task_id)
            self.progress.update(task_id, visible=False)
        elif task_id in self.invisible_tasks:
            self.invisible_tasks.remove(task_id)
        elif task_id == self.overflow_task_id:
            self.overflow.update(task_id, visible=False)
        else:
            raise ValueError("Task ID not found")
        await self.redraw()

    async def mark_task_completed(self, task_id: TaskID) -> None:
        self.progress.update(task_id, visible=False)
        if task_id in self.visible_tasks:
            self.visible_tasks.remove(task_id)
        elif task_id in self.invisible_tasks:
            self.invisible_tasks.remove(task_id)
        await self.redraw()
        self.completed_tasks.append(task_id)

    async def advance_file(self, task_id: TaskID, amount: int) -> None:
        if task_id in self.uninitiated_tasks:
            self.uninitiated_tasks.remove(task_id)
            self.invisible_tasks.append(task_id)
            await self.redraw()
        self.progress.advance(task_id, amount)

    async def update_file_length(self, task_id: TaskID, total: int) -> None:
        if task_id in self.invisible_tasks:
            self.progress.update(task_id, total=total, visible=False)
        elif task_id in self.visible_tasks:
            self.progress.update(task_id, total=total, visible=True)
        elif task_id in self.uninitiated_tasks:
            self.progress.update(task_id, total=total, visible=False)
            self.uninitiated_tasks.remove(task_id)
            self.invisible_tasks.append(task_id)
            await self.redraw()


class ScreenMaster:
    def __init__(self, progress_options: Dict):
        self.hide_overall_progress = progress_options['hide_overall_progress']
        self.hide_file_progress = progress_options['hide_file_progress']
        self.refresh_rate = progress_options['refresh_rate']

        self.Progressions = Progressions()
        self.OverallFileProgress = OverallFileProgress(0, self.Progressions.overall_file_progress)
        self.FileProgress = FileProgress(self.Progressions, progress_options['visible_rows_files'])

    async def get_layout(self) -> Layout:
        """Table creator for forum threads"""
        progress_layout = Layout()
        progress_layout.split_column(
            Layout(name="upper", ratio=1),
            Layout(name="Scraping", ratio=1),
            Layout(renderable=await self.Progressions.get_file_progress(), name="Downloads", ratio=1),
        )
        progress_layout["upper"].split_row(
            Layout(renderable=await self.Progressions.get_overall_progress(), name="Files", ratio=1),
            Layout(name="Scrape Failures", ratio=1),
            Layout(name="Download Failures", ratio=1),
        )

        return progress_layout
