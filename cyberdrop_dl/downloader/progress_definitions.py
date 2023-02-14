from __future__ import annotations

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

overall_file_progress = Progress("[progress.description]{task.description}",
                                 BarColumn(bar_width=None),
                                 "[progress.percentage]{task.percentage:>3.2f}%",
                                 "{task.completed} of {task.total} Files Completed")

file_progress = Progress(SpinnerColumn(),
                         "[progress.description]{task.description}",
                         BarColumn(bar_width=None),
                         "[progress.percentage]{task.percentage:>3.2f}%",
                         "━",
                         DownloadColumn(),
                         "━",
                         TransferSpeedColumn(),
                         "━",
                         TimeRemainingColumn())


async def get_forum_table(progress_options: dict):
    """Table creator for forum threads"""
    progress_table = Table.grid(expand=True)
    if not progress_options['dont_show_overall_progress']:
        progress_table.add_row(Panel.fit(overall_file_progress, title="Overall Progress", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_forum_progress']:
        progress_table.add_row(Panel.fit(forum_progress, title="Total Thread", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_thread_progress']:
        progress_table.add_row(Panel.fit(cascade_progress, title="Current Thread", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_domain_progress']:
        progress_table.add_row(Panel.fit(domain_progress, title="Domains Being Downloaded", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_album_progress']:
        progress_table.add_row(Panel.fit(album_progress, title="Albums Being Downloaded", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_file_progress']:
        progress_table.add_row(Panel.fit(file_progress, title="[b]Files Being Downloaded", border_style="green", padding=(1, 1)))
    return progress_table


async def get_cascade_table(progress_options: dict):
    """Table creator for cascade objects"""
    progress_table = Table.grid(expand=True)
    if not progress_options['dont_show_overall_progress']:
        progress_table.add_row(Panel.fit(overall_file_progress, title="Overall Progress", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_thread_progress']:
        progress_table.add_row(Panel.fit(cascade_progress, title="Current Thread", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_domain_progress']:
        progress_table.add_row(Panel.fit(domain_progress, title="Domains Being Downloaded", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_album_progress']:
        progress_table.add_row(Panel.fit(album_progress, title="Albums Being Downloaded", border_style="green", padding=(1, 1)))
    if not progress_options['dont_show_file_progress']:
        progress_table.add_row(Panel.fit(file_progress, title="[b]Files Being Downloaded", border_style="green", padding=(1, 1)))
    return progress_table
