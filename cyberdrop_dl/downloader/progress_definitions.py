from rich.panel import Panel
from rich.progress import Progress, BarColumn, SpinnerColumn, TransferSpeedColumn, DownloadColumn, TimeRemainingColumn
from rich.table import Table

forum_progress = Progress("[progress.description]{task.description}",
                         BarColumn(bar_width=None),
                         "[progress.percentage]{task.percentage:>3.2f}%",
                         "{task.completed} of {task.total} Threads Completed")

cascade_progress = Progress("[progress.description]{task.description}",
                            BarColumn(bar_width=None),
                            "[progress.percentage]{task.percentage:>3.2f}%",
                            "{task.completed} of {task.total} Domains Completed")

domain_progress = Progress("[progress.description]{task.description}",
                           BarColumn(bar_width=None),
                           "[progress.percentage]{task.percentage:>3.2f}%",
                           "{task.completed} of {task.total} Albums Completed")

album_progress = Progress("[progress.description]{task.description}",
                          BarColumn(bar_width=None),
                          "[progress.percentage]{task.percentage:>3.2f}%",
                          "{task.completed} of {task.total} Files Completed")

file_progress = Progress(SpinnerColumn(),
                         "[progress.description]{task.description}",
                         BarColumn(bar_width=None),
                         "[progress.percentage]{task.percentage:>3.2f}%",
                         "•",
                         DownloadColumn(),
                         "•",
                         TransferSpeedColumn(),
                         "•",
                         TimeRemainingColumn())


async def get_forum_table():
    """Table creator for forum threads"""
    progress_table = Table.grid(expand=True)
    progress_table.add_row(Panel.fit(forum_progress, title="Total Thread", border_style="green", padding=(1, 1)))
    progress_table.add_row(Panel.fit(cascade_progress, title="Current Thread", border_style="green", padding=(1, 1)))
    progress_table.add_row(Panel.fit(domain_progress, title="Domains Being Downloaded", border_style="green", padding=(1, 1)))
    progress_table.add_row(Panel.fit(album_progress, title="Albums Being Downloaded", border_style="green", padding=(1, 1)))
    progress_table.add_row(Panel.fit(file_progress, title="[b]Files Being Downloaded", border_style="green", padding=(1, 1)))
    return progress_table


async def get_cascade_table():
    """Table creator for cascade objects"""
    progress_table = Table.grid(expand=True)
    progress_table.add_row(Panel.fit(cascade_progress, title="Current Thread", border_style="green", padding=(1, 1)))
    progress_table.add_row(Panel.fit(domain_progress, title="Domains Being Downloaded", border_style="green", padding=(1, 1)))
    progress_table.add_row(Panel.fit(album_progress, title="Albums Being Downloaded", border_style="green", padding=(1, 1)))
    progress_table.add_row(Panel.fit(file_progress, title="[b]Files Being Downloaded", border_style="green", padding=(1, 1)))
    return progress_table
