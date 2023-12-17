from dataclasses import field
from typing import TYPE_CHECKING

from rich.layout import Layout

from cyberdrop_dl.ui.progress.downloads_progress import DownloadsProgress
from cyberdrop_dl.ui.progress.file_progress import FileProgress
from cyberdrop_dl.ui.progress.scraping_progress import ScrapingProgress
from cyberdrop_dl.ui.progress.statistic_progress import DownloadStatsProgress, ScrapeStatsProgress
from cyberdrop_dl.utils.utilities import log_with_color

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager


class ProgressManager:
    def __init__(self, manager: 'Manager'):
        # File Download Bars
        self.file_progress: FileProgress = FileProgress(5, manager)

        # Scraping Printout
        self.scraping_progress: ScrapingProgress = ScrapingProgress(5, manager)

        # Overall Progress Bars & Stats
        self.download_progress: DownloadsProgress = DownloadsProgress()
        self.download_stats_progress: DownloadStatsProgress = DownloadStatsProgress()
        self.scrape_stats_progress: ScrapeStatsProgress = ScrapeStatsProgress()

        self.layout: Layout = field(init=False)

    async def startup(self) -> None:
        """Startup process for the progress manager"""
        progress_layout = Layout()
        progress_layout.split_column(
            Layout(name="upper", ratio=1, minimum_size=8),
            Layout(renderable=await self.scraping_progress.get_progress(), name="Scraping", ratio=2),
            Layout(renderable=await self.file_progress.get_progress(), name="Downloads", ratio=2),
        )
        progress_layout["upper"].split_row(
            Layout(renderable=await self.download_progress.get_progress(), name="Files", ratio=1),
            Layout(renderable=await self.scrape_stats_progress.get_progress(), name="Scrape Failures", ratio=1),
            Layout(renderable=await self.download_stats_progress.get_progress(), name="Download Failures", ratio=1),
        )

        self.layout = progress_layout

    async def print_stats(self) -> None:
        """Prints the stats of the program"""
        await log_with_color("\nDownload Stats:", "cyan", 20)
        await log_with_color(f"Downloaded {self.download_progress.completed_files} files", "green", 20)
        await log_with_color(f"Previously Downloaded {self.download_progress.previously_completed_files} files", "yellow", 20)
        await log_with_color(f"Skipped By Config {self.download_progress.skipped_files} files", "yellow", 20)
        await log_with_color(f"Failed {self.download_stats_progress.failed_files} files", "red", 20)

        scrape_failures = await self.scrape_stats_progress.return_totals()
        await log_with_color("\nScrape Failures:", "cyan", 20)
        for key, value in scrape_failures.items():
            await log_with_color(f"Scrape Failures ({key}): {value}", "red", 20)

        download_failures = await self.download_stats_progress.return_totals()
        await log_with_color("\nDownload Failures:", "cyan", 20)
        for key, value in download_failures.items():
            await log_with_color(f"Download Failures ({key}): {value}", "red", 20)