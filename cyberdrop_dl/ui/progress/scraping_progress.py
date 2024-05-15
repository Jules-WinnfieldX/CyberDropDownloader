from typing import List, TYPE_CHECKING

from rich.console import Group
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TaskID
from yarl import URL

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


async def adjust_title(s: str, length: int = 40, placeholder: str = "...") -> str:
    """Collapse and truncate or pad the given string to fit in the given length"""
    return f"{s[:length - len(placeholder)]}{placeholder}" if len(s) >= length else s.ljust(length)


class ScrapingProgress:
    """Class that manages the download progress of individual files"""
    def __init__(self, visible_tasks_limit: int, manager: 'Manager'):
        self.manager = manager

        self.progress = Progress(SpinnerColumn(),
                                 "[progress.description]{task.description}")
        self.overflow = Progress("[progress.description]{task.description}")
        self.queue = Progress("[progress.description]{task.description}")
        self.progress_group = Group(self.progress, self.overflow, self.queue)

        self.color = "plum3"
        self.type_str = "Files"
        self.progress_str = "[{color}]{description}"
        self.overflow_str = "[{color}]... And {number} Other Links"
        self.queue_str = "[{color}]... And {number} Links In Scrape Queue"
        self.overflow_task_id = self.overflow.add_task(self.overflow_str.format(color=self.color, number=0, type_str=self.type_str), visible=False)
        self.queue_task_id = self.queue.add_task(self.queue_str.format(color=self.color, number=0, type_str=self.type_str), visible=False)

        self.visible_tasks: List[TaskID] = []
        self.invisible_tasks: List[TaskID] = []
        self.tasks_visibility_limit = visible_tasks_limit

    async def get_progress(self) -> Panel:
        """Returns the progress bar"""
        return Panel(self.progress_group, title="Scraping", border_style="green", padding=(1, 1))

    async def get_queue_length(self) -> int:
        """Returns the number of tasks in the scraper queue"""
        total = 0

        for scraper in self.manager.scrape_mapper.existing_crawlers.values():
            total += scraper.waiting_items

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
            await self.manager.progress_manager.file_progress.redraw(True)

    async def add_task(self, url: URL) -> TaskID:
        """Adds a new task to the progress bar"""
        if len(self.visible_tasks) >= self.tasks_visibility_limit:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=str(url)), visible=False)
            self.invisible_tasks.append(task_id)
        else:
            task_id = self.progress.add_task(self.progress_str.format(color=self.color, description=str(url)))
            self.visible_tasks.append(task_id)
        await self.redraw()
        return task_id

    async def remove_task(self, task_id: TaskID) -> None:
        """Removes a task from the progress bar"""
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
