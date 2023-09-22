import asyncio
import contextlib
import logging
import os

import aiorun
from rich import console
from rich.live import Live

from cyberdrop_dl.managers.manager import Manager
from cyberdrop_dl.scraper.scraper import ScrapeMapper
from cyberdrop_dl.ui.ui import program_ui
from cyberdrop_dl.utils.sorting import Sorter
from cyberdrop_dl.utils.utilities import check_latest_pypi, log_with_color, check_partials_and_empty_folders


def startup() -> Manager:
    """
    Starts the program and returns the manager
    This will also run the UI for the program
    After this function returns, the manager will be ready to use and scraping / downloading can begin
    """

    try:
        manager = Manager()
        manager.startup()

        if not manager.args_manager.immediate_download:
            program_ui(manager)

        logging.basicConfig(
            filename=manager.file_manager.main_log,
            level=logging.DEBUG,
            format="%(asctime)s:%(levelname)s:%(module)s:%(filename)s:%(lineno)d:%(message)s",
            filemode="w",
        )

        return manager

    except KeyboardInterrupt:
        print("\nExiting...")
        exit(0)


async def runtime(manager: Manager) -> None:
    """Main runtime loop for the program, this will run until all scraping and downloading is complete"""
    scrape_mapper = ScrapeMapper(manager)
    download_manager = manager.download_manager
    asyncio.create_task(scrape_mapper.map_urls())

    await scrape_mapper.load_links()
    while True:
        if await scrape_mapper.check_complete() and await download_manager.check_complete():
            break
        await asyncio.sleep(1)


async def director(manager: Manager) -> None:
    """Runs the program and handles the UI"""
    await manager.async_startup()

    with Live(manager.progress_manager.layout, refresh_per_second=10):
        await runtime(manager)

        clear_screen_proc = await asyncio.create_subprocess_shell('cls' if os.name == 'nt' else 'clear')
        await clear_screen_proc.wait()

        if manager.config_manager.settings_data['Sorting']['sort_downloads']:
            sorter = Sorter(manager.directory_manager.downloads, manager.directory_manager.sorted_downloads,
                            manager.config_manager.settings_data['Sorting']['sorted_audio_folder'],
                            manager.config_manager.settings_data['Sorting']['sorted_image_folder'],
                            manager.config_manager.settings_data['Sorting']['sorted_video_folder'],
                            manager.config_manager.settings_data['Sorting']['sorted_other_folder'])
            await sorter.sort()
        await check_partials_and_empty_folders(manager)

        await manager.progress_manager.print_stats()
        await check_latest_pypi()

        await log_with_color("Finished downloading. Enjoy :)", 'green')

        asyncio.get_event_loop().stop()


def main():
    manager = startup()

    with contextlib.suppress(RuntimeError, asyncio.CancelledError):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        aiorun.run(director(manager), stop_on_unhandled_errors=True)
        exit(0)


if __name__ == '__main__':
    main()
