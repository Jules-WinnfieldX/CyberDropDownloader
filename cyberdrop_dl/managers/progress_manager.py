from dataclasses import field
from typing import Dict

from rich.layout import Layout

from cyberdrop_dl.ui.progress.downloads_progress import DownloadsProgress
from cyberdrop_dl.ui.progress.file_progress import FileProgress
from cyberdrop_dl.ui.progress.scraping_progress import ScrapingProgress
from cyberdrop_dl.ui.progress.statistic_progress import DownloadStatsProgress, ScrapeStatsProgress


class ProgressManager:
    def __init__(self, progress_options: Dict):
        self.refresh_rate = progress_options['refresh_rate']

        # File Download Bars
        self.file_progress: FileProgress = FileProgress(5)

        # Scraping Printout
        self.scraping_progress: ScrapingProgress = ScrapingProgress(5)

        # Overall Progress Bars & Stats
        self.download_progress: DownloadsProgress = DownloadsProgress()
        self.download_stats_progress: DownloadStatsProgress = DownloadStatsProgress()
        self.scrape_stats_progress: ScrapeStatsProgress = ScrapeStatsProgress()

        self.layout: Layout = field(init=False)

    async def startup(self):
        progress_layout = Layout()
        progress_layout.split_column(
            Layout(name="upper", ratio=1),
            Layout(renderable=await self.scraping_progress.get_progress(), name="Scraping", ratio=1),
            Layout(renderable=await self.file_progress.get_progress(), name="Downloads", ratio=1),
        )
        progress_layout["upper"].split_row(
            Layout(renderable=await self.download_progress.get_progress(), name="Files", ratio=1),
            Layout(renderable=await self.scrape_stats_progress.get_progress(), name="Scrape Failures", ratio=1),
            Layout(renderable=await self.download_stats_progress.get_progress(), name="Download Failures", ratio=1),
        )

        self.layout = progress_layout
