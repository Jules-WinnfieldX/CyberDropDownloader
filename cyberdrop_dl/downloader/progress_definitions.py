from __future__ import annotations

import contextlib
from typing import Dict, List, Optional, Tuple

from rich.console import Group
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
from rich.table import Table


def adjust_title(s: str, length: int = 40, placeholder: str = "...") -> str:
    """Collapse and truncate or pad the given string to fit in the given length"""
    return f"{s[:length - len(placeholder)]}{placeholder}" if len(s) >= length else s.ljust(length)


class Progressions:
    def __init__(self):
        self.overall_file_progress = Progress("[progress.description]{task.description}",
                                              BarColumn(bar_width=None),
                                              "[progress.percentage]{task.percentage:>3.2f}%",
                                              "{task.completed} of {task.total} Files Completed")

        self.forum_progress = Progress("[progress.description]{task.description}",
                                       BarColumn(bar_width=None),
                                       "[progress.percentage]{task.percentage:>3.2f}%",
                                       "{task.completed} of {task.total} Threads Completed")
        self.forum_progress_overflow = Progress("[progress.description]{task.description}")

        self.cascade_progress = Progress("[progress.description]{task.description}",
                                         BarColumn(bar_width=None),
                                         "[progress.percentage]{task.percentage:>3.2f}%",
                                         "{task.completed} of {task.total} Domains Completed")
        self.cascade_progress_overflow = Progress("[progress.description]{task.description}")

        self.domain_progress = Progress("[progress.description]{task.description}",
                                        BarColumn(bar_width=None),
                                        "[progress.percentage]{task.percentage:>3.2f}%",
                                        "{task.completed} of {task.total} Albums Completed")
        self.domain_progress_overflow = Progress("[progress.description]{task.description}")

        self.album_progress = Progress("[progress.description]{task.description}",
                                       BarColumn(bar_width=None),
                                       "[progress.percentage]{task.percentage:>3.2f}%",
                                       "{task.completed} of {task.total} Files Completed")
        self.album_progress_overflow = Progress("[progress.description]{task.description}")

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

    async def get_overall_progress(self) -> Panel:
        return Panel(Group(self.overall_file_progress), title="Overall Progress", border_style="green", padding=(1, 1))

    async def get_forum_progress(self) -> Panel:
        return Panel(Group(self.forum_progress), title="Total Threads", border_style="green",padding=(1, 1))

    async def get_cascade_progress(self) -> Panel:
        return Panel(Group(self.cascade_progress, self.cascade_progress_overflow), title="Current Threads", border_style="green", padding=(1, 1))

    async def get_domain_progress(self) -> Panel:
        return Panel(Group(self.domain_progress, self.domain_progress_overflow), title="Current Domains", border_style="green", padding=(1, 1))

    async def get_album_progress(self) -> Panel:
        return Panel(Group(self.album_progress, self.album_progress_overflow), title="Current Albums", border_style="green", padding=(1, 1))

    async def get_file_progress(self) -> Panel:
        return Panel(Group(self.file_progress, self.file_progress_overflow), title="Current Downloads", border_style="green", padding=(1, 1))


class OverallFileProgress:
    """Class that keeps track of completed, skipped and failed files"""

    def __init__(self, total_files: int, overall_file_progress: Progress):
        self.overall_file_progress = overall_file_progress

        self.completed_files_task_id = overall_file_progress.add_task("[green]Completed", total=total_files)
        self.completed_files = 0
        self.skipped_files_task_id = overall_file_progress.add_task("[yellow]Skipped", total=total_files)
        self.skipped_files = 0
        self.failed_files_task_id = overall_file_progress.add_task("[red]Failed", total=total_files)
        self.failed_files = 0

    async def update_total(self, total_files: int) -> None:
        self.overall_file_progress.update(self.completed_files_task_id, total=total_files)
        self.overall_file_progress.update(self.skipped_files_task_id, total=total_files)
        self.overall_file_progress.update(self.failed_files_task_id, total=total_files)

    async def add_completed(self) -> None:
        self.overall_file_progress.advance(self.completed_files_task_id, 1)
        self.completed_files += 1

    async def add_skipped(self) -> None:
        self.overall_file_progress.advance(self.skipped_files_task_id, 1)
        self.skipped_files += 1

    async def add_failed(self) -> None:
        self.overall_file_progress.advance(self.failed_files_task_id, 1)
        self.failed_files += 1

    async def return_totals(self) -> Tuple[int, int, int]:
        return self.completed_files, self.skipped_files, self.failed_files

    async def hide(self) -> None:
        self.overall_file_progress.update(self.completed_files_task_id, visible=False)
        self.overall_file_progress.update(self.skipped_files_task_id, visible=False)
        self.overall_file_progress.update(self.failed_files_task_id, visible=False)


class _Progress:
    def __init__(self, progress: Progress, overflow: Progress, color: str, type_str: str, visible_tasks_limit: int):
        self.color = color
        self.type_str = type_str

        self.progress = progress
        self.progress_str = "[{color}]{description}"
        self.overflow = overflow
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

    async def add_task(self, description: str, total: int, initiated: bool) -> TaskID:
        if not initiated:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=description), total=total, visible=False)
            self.uninitiated_tasks.append(task_id)
        elif len(self.visible_tasks) >= self.tasks_visibility_limit:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=description), total=total, visible=False)
            self.invisible_tasks.append(task_id)
        else:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=description), total=total)
            self.visible_tasks.append(task_id)
        return task_id

    async def remove_task(self, task_id: TaskID) -> None:
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

    async def advance_task(self, task_id: TaskID, amount: int) -> None:
        if task_id in self.uninitiated_tasks:
            self.uninitiated_tasks.remove(task_id)
            self.invisible_tasks.append(task_id)
            await self.redraw()
        self.progress.advance(task_id, amount)

    async def update_total(self, task_id: TaskID, total: int) -> None:
        if task_id in self.invisible_tasks:
            self.progress.update(task_id, total=total, visible=False)
        elif task_id in self.visible_tasks:
            self.progress.update(task_id, total=total, visible=True)
        elif task_id in self.uninitiated_tasks:
            self.progress.update(task_id, total=total, visible=False)
            self.uninitiated_tasks.remove(task_id)
            self.invisible_tasks.append(task_id)
            await self.redraw()


class ForumProgress:
    def __init__(self, progressions: Progressions):
        self.forum_progress = progressions.forum_progress
        self.color = "orange3"
        self.type_str = "Threads"
        self.progress = _Progress(self.forum_progress, progressions.forum_progress_overflow, self.color, "Threads", 5)

    async def add_forum(self, total_tasks: int) -> TaskID:
        return await self.progress.add_task("FORUM THREADS", total_tasks, True)

    async def advance_forum(self, task_id: TaskID) -> None:
        await self.progress.advance_task(task_id, 1)


class CascadeProgress:
    """Class that manages forum progression"""

    def __init__(self, progressions: Progressions, visible_tasks_limit: int):
        self.cascade_progress = progressions.cascade_progress
        self.color = "light_salmon3"
        self.type_str = "Threads"
        self.progress = _Progress(self.cascade_progress, progressions.cascade_progress_overflow, self.color, "Threads", visible_tasks_limit)

    async def add_cascade(self, title: str, total_domains: int) -> TaskID:
        task_id = await self.progress.add_task(title.upper(), total_domains, True)
        await self.progress.redraw()
        return task_id

    async def advance_cascade(self, task_id: TaskID) -> None:
        await self.progress.advance_task(task_id, 1)

    async def mark_cascade_completed(self, task_id: TaskID) -> None:
        await self.progress.mark_task_completed(task_id)
        await self.progress.redraw()


class DomainProgress:
    def __init__(self, progressions: Progressions, visible_tasks_limit: int):
        self.domain_progress = progressions.domain_progress
        self.color = "light_pink3"
        self.type_str = "Domains"
        self.progress = _Progress(self.domain_progress, progressions.domain_progress_overflow, self.color, "Domains", visible_tasks_limit)

        self.domains: Dict[str, TaskID] = {}
        self.domain_totals: Dict[str, int] = {}

    async def add_domain(self, domain: str, total_albums: int) -> TaskID:
        if domain in self.domains:
            self.domain_totals[domain] += total_albums
            await self.progress.update_total(self.domains[domain], self.domain_totals[domain])
        else:
            self.domains[domain] = await self.progress.add_task(domain.upper(), total_albums, True)
            self.domain_totals[domain] = total_albums

        await self.progress.redraw()
        return self.domains[domain]

    async def advance_domain(self, task_id: TaskID) -> None:
        await self.progress.advance_task(task_id, 1)

    async def mark_domain_completed(self, domain: str, task_id: TaskID) -> None:
        task = [x for x in self.domain_progress.tasks if x.id == task_id][0]
        if task.finished:
            with contextlib.suppress(KeyError):
                self.domains.pop(domain)
                self.domain_totals.pop(domain)
            await self.progress.mark_task_completed(task_id)


class AlbumProgress:
    def __init__(self, progressions: Progressions, visible_tasks_limit: int):
        self.album_progress = progressions.album_progress
        self.color = "pink3"
        self.type_str = "Albums"
        self.progress = _Progress(self.album_progress, progressions.album_progress_overflow, self.color, "Albums", visible_tasks_limit)

        self.albums: Dict[str, TaskID] = {}
        self.albums_totals: Dict[str, int] = {}

    async def add_album(self, album: str, total_files: int) -> TaskID:
        task_description = album.split('/')[-1]
        task_description = task_description.encode("ascii", "ignore").decode().strip()
        task_description = adjust_title(task_description).upper().strip()

        if task_description in self.albums:
            self.albums_totals[task_description] += total_files
            await self.progress.update_total(self.albums[task_description], self.albums_totals[task_description])
        else:
            self.albums[task_description] = await self.progress.add_task(task_description, total_files, True)
            self.albums_totals[task_description] = total_files

        await self.progress.redraw()
        return self.albums[task_description]

    async def advance_album(self, task_id: TaskID) -> None:
        await self.progress.advance_task(task_id, 1)

    async def mark_album_completed(self, album: str, task_id: TaskID) -> None:
        task_description = album.split('/')[-1]
        task_description = task_description.encode("ascii", "ignore").decode().strip()
        task_description = adjust_title(task_description).upper()

        task = [x for x in self.album_progress.tasks if x.id == task_id][0]
        if task.finished:
            with contextlib.suppress(KeyError):
                self.albums.pop(task_description)
                self.albums_totals.pop(task_description)
            await self.progress.mark_task_completed(task_id)


class FileProgress:
    def __init__(self, progressions: Progressions, visible_tasks_limit: int):
        self.file_progress = progressions.file_progress
        self.color = "plum3"
        self.type_str = "Files"
        self.progress = _Progress(self.file_progress, progressions.file_progress_overflow, self.color, "Files", visible_tasks_limit)

    async def add_file(self, file: str, expected_size: Optional[int]) -> TaskID:
        task_description = file.split('/')[-1]
        task_description = task_description.encode("ascii", "ignore").decode().strip()
        task_description = adjust_title(task_description)

        task_id = await self.progress.add_task(task_description.upper(), expected_size if expected_size else 0, False)
        await self.progress.redraw()
        return task_id

    async def update_file_length(self, task_id: TaskID, length: int) -> None:
        await self.progress.update_total(task_id, length)

    async def advance_file(self, task_id: TaskID, increment: int) -> None:
        await self.progress.advance_task(task_id, increment)

    async def remove_file(self, task_id: TaskID) -> None:
        await self.progress.remove_task(task_id)
        await self.progress.redraw()

    async def mark_file_completed(self, task_id: TaskID) -> None:
        await self.progress.mark_task_completed(task_id)
        await self.progress.redraw()


class ProgressMaster:
    def __init__(self, progress_options: Dict):
        self.hide_overall_progress = progress_options['hide_overall_progress']
        self.hide_forum_progress = progress_options['hide_forum_progress']
        self.hide_thread_progress = progress_options['hide_thread_progress']
        self.hide_domain_progress = progress_options['hide_domain_progress']
        self.hide_album_progress = progress_options['hide_album_progress']
        self.hide_file_progress = progress_options['hide_file_progress']
        self.refresh_rate = progress_options['refresh_rate']

        self.Progressions = Progressions()
        self.OverallFileProgress = OverallFileProgress(0, self.Progressions.overall_file_progress)
        self.ForumProgress = ForumProgress(self.Progressions)
        self.CascadeProgress = CascadeProgress(self.Progressions, progress_options['visible_rows_threads'])
        self.DomainProgress = DomainProgress(self.Progressions, progress_options['visible_rows_domains'])
        self.AlbumProgress = AlbumProgress(self.Progressions, progress_options['visible_rows_albums'])
        self.FileProgress = FileProgress(self.Progressions, progress_options['visible_rows_files'])

    async def get_table(self) -> Table:
        """Table creator for forum threads"""
        progress_table = Table.grid(expand=True)
        if not self.hide_overall_progress:
            progress_table.add_row(await self.Progressions.get_overall_progress())
        if not self.hide_forum_progress:
            progress_table.add_row(await self.Progressions.get_forum_progress())
        if not self.hide_thread_progress:
            progress_table.add_row(await self.Progressions.get_cascade_progress())
        if not self.hide_domain_progress:
            progress_table.add_row(await self.Progressions.get_domain_progress())
        if not self.hide_album_progress:
            progress_table.add_row(await self.Progressions.get_album_progress())
        if not self.hide_file_progress:
            progress_table.add_row(await self.Progressions.get_file_progress())
        return progress_table
