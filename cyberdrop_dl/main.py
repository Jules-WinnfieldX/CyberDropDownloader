import asyncio
import contextlib
import logging

import aiorun
from rich.live import Live

from cyberdrop_dl.managers.manager import Manager
from cyberdrop_dl.scraper.scraper import ScrapeMapper
from cyberdrop_dl.ui.ui import program_ui


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

    while True:
        if scrape_mapper.complete and download_manager.check_complete():
            break
        await asyncio.sleep(1)


async def director(manager: Manager) -> None:
    """Runs the program and handles the UI"""
    await manager.async_startup()

    with Live(manager.progress_manager.layout, refresh_per_second=10):
        await runtime(manager)


def main():
    manager = startup()

    with contextlib.suppress(RuntimeError, asyncio.CancelledError):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        aiorun.run(director(manager))
        exit(0)


if __name__ == '__main__':
    main()
