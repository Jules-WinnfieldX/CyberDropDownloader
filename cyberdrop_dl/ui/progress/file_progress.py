from typing import List, Optional, TYPE_CHECKING

from rich.console import Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, \
    TaskID

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


async def adjust_title(s: str, length: int = 40, placeholder: str = "...") -> str:
    """Collapse and truncate or pad the given string to fit in the given length"""
    return f"{s[:length - len(placeholder)]}{placeholder}" if len(s) >= length else s.ljust(length)


class FileProgress:
    """Class that manages the download progress of individual files"""
    def __init__(self, visible_tasks_limit: int, manager: 'Manager'):
        self.manager = manager

        self.progress = Progress(SpinnerColumn(),
                                 "[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "━",
                                 DownloadColumn(),
                                 "━",
                                 TransferSpeedColumn(),
                                 "━",
                                 TimeRemainingColumn())
        self.overflow = Progress("[progress.description]{task.description}")
        self.queue = Progress("[progress.description]{task.description}")
        self.progress_group = Group(self.progress, self.overflow, self.queue)

        self.color = "plum3"
        self.type_str = "Files"
        self.progress_str = "[{color}]{description}"
        self.overflow_str = "[{color}]... And {number} Other {type_str}"
        self.queue_str = "[{color}]... And {number} {type_str} In Download Queue"
        self.overflow_task_id = self.overflow.add_task(self.overflow_str.format(color=self.color, number=0, type_str=self.type_str), visible=False)
        self.queue_task_id = self.queue.add_task(self.queue_str.format(color=self.color, number=0, type_str=self.type_str), visible=False)

        self.visible_tasks: List[TaskID] = []
        self.invisible_tasks: List[TaskID] = []
        self.completed_tasks: List[TaskID] = []
        self.uninitiated_tasks: List[TaskID] = []
        self.tasks_visibility_limit = visible_tasks_limit

    async def get_progress(self) -> Panel:
        """Returns the progress bar"""
        return Panel(self.progress_group, title="Downloads", border_style="green", padding=(1, 1))

    async def get_queue_length(self) -> int:
        """Returns the number of tasks in the downloader queue"""
        total = 0

        for scraper in self.manager.scrape_mapper.existing_crawlers.values():
            total += scraper.downloader.waiting_items

        return total

    async def redraw(self, passed=False) -> None:
        """Redraws the progress bar"""
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

        queue_length = await self.get_queue_length()
        if queue_length > 0:
            self.queue.update(self.queue_task_id, description=self.queue_str.format(color=self.color, number=queue_length, type_str=self.type_str), visible=True)
        else:
            self.queue.update(self.queue_task_id, visible=False)
        
        if not passed:
            await self.manager.progress_manager.scraping_progress.redraw(True)

    async def add_task(self, file: str, expected_size: Optional[int]) -> TaskID:
        """Adds a new task to the progress bar"""
        description = file.split('/')[-1]
        description = description.encode("ascii", "ignore").decode().strip()
        description = await adjust_title(description)

        if len(self.visible_tasks) >= self.tasks_visibility_limit:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=description), total=expected_size, visible=False)
            self.invisible_tasks.append(task_id)
        else:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=description), total=expected_size)
            self.visible_tasks.append(task_id)
        await self.redraw()
        return task_id

    async def remove_file(self, task_id: TaskID) -> None:
        """Removes the given task from the progress bar"""
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
        """Marks the given task as completed"""
        self.progress.update(task_id, visible=False)
        if task_id in self.visible_tasks:
            self.visible_tasks.remove(task_id)
        elif task_id in self.invisible_tasks:
            self.invisible_tasks.remove(task_id)
        await self.redraw()
        self.completed_tasks.append(task_id)

    async def advance_file(self, task_id: TaskID, amount: int) -> None:
        """Advances the progress of the given task by the given amount"""
        if task_id in self.uninitiated_tasks:
            self.uninitiated_tasks.remove(task_id)
            self.invisible_tasks.append(task_id)
            await self.redraw()
        self.progress.advance(task_id, amount)

    async def update_file_length(self, task_id: TaskID, total: int) -> None:
        """Updates the total number of bytes to be downloaded for the given task"""
        if task_id in self.invisible_tasks:
            self.progress.update(task_id, total=total, visible=False)
        elif task_id in self.visible_tasks:
            self.progress.update(task_id, total=total, visible=True)
        elif task_id in self.uninitiated_tasks:
            self.progress.update(task_id, total=total, visible=False)
            self.uninitiated_tasks.remove(task_id)
            self.invisible_tasks.append(task_id)
            await self.redraw()
