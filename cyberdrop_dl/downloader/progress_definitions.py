from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn, SpinnerColumn, TransferSpeedColumn, \
    FileSizeColumn, TotalFileSizeColumn, DownloadColumn


class CascadeProgress(Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "cascade":
                self.columns = (
                    "{task.completed} of {task.total} Domains Completed",
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.2f}%"
                )
            if task.fields.get("progress_type") == "domain":
                self.columns = (
                    "├─",
                    "[progress.description]{task.description}",
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "{task.completed} of {task.total} Albums Completed"
                )
            if task.fields.get("progress_type") == "domain_summary":
                self.columns = (
                    "├─",
                    "[progress.description]{task.description}",
                    "{task.completed} of {task.total} Albums Completed"
                )
            if task.fields.get("progress_type") == "album":
                self.columns = (
                    "├──",
                    "[progress.description]{task.description}",
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "{task.completed} of {task.total} Files Completed"
                )
            if task.fields.get("progress_type") == "file":
                self.columns = (
                    "├───", SpinnerColumn(),
                    "[progress.description]{task.description}",
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn()
                )
            yield self.make_tasks_table([task])


class ForumsProgress(Progress):
    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "forum":
                self.columns = (
                    "[progress.description]{task.description}",
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "{task.completed} of {task.total} Threads Completed",
                )
            if task.fields.get("progress_type") == "cascade":
                self.columns = (
                    "├─",
                    "[progress.description]{task.description}",
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "{task.completed} of {task.total} Domains Completed",
                )
            if task.fields.get("progress_type") == "domain":
                self.columns = (
                    "├──",
                    "[progress.description]{task.description}",
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "{task.completed} of {task.total} Albums Completed",
                )
            if task.fields.get("domain_updated"):
                self.columns = (
                    "├──",
                    "[progress.description]{task.description}",
                    "{task.completed} of {task.total} Albums Completed",
                )
            if task.fields.get("progress_type") == "album":
                self.columns = (
                    "├───",
                    "[progress.description]{task.description}",
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "{task.completed} of {task.total} Files Completed",
                )
            if task.fields.get("progress_type") == "file":
                self.columns = (
                    "├────", SpinnerColumn(),
                    "[progress.description]{task.description}",
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.2f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn()
                )
            yield self.make_tasks_table([task])
