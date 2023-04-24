import asyncio
import itertools
from pathlib import Path

from .base_functions import FILE_FORMATS, log, purge_dir


class Sorter:
    def __init__(self, download_dir: Path, sorted_downloads: Path, audio_dir: str, image_dir: str, video_dir: str,
                 other_dir: str):
        self.download_dir = download_dir
        self.sorted_downloads = sorted_downloads

        self.audio_dir = audio_dir
        self.image_dir = image_dir
        self.video_dir = video_dir
        self.other_dir = other_dir

        self.audio = 0
        self.images = 0
        self.videos = 0
        self.other = 0

    async def find_files_in_dir(self, directory: Path):
        file_list = []
        for x in directory.iterdir():
            if x.is_file():
                file_list.append(x)
            elif x.is_dir():
                file_list.extend(await self.find_files_in_dir(x))
        return file_list

    async def sort(self):
        for folder in self.download_dir.iterdir():
            if not folder.is_dir():
                continue

            audio_destination = Path(self.audio_dir.format(sort_dir=self.sorted_downloads, base_dir=folder.name))
            image_destination = Path(self.image_dir.format(sort_dir=self.sorted_downloads, base_dir=folder.name))
            video_destination = Path(self.video_dir.format(sort_dir=self.sorted_downloads, base_dir=folder.name))
            other_destination = Path(self.other_dir.format(sort_dir=self.sorted_downloads, base_dir=folder.name))

            files = await self.find_files_in_dir(folder)
            for file in files:
                ext = file.suffix.lower()
                if '.part' in ext:
                    continue
                elif ext in FILE_FORMATS['Audio']:
                    audio_destination.mkdir(parents=True, exist_ok=True)
                    await self.move_cd(file, audio_destination)
                    self.audio += 1
                elif ext in FILE_FORMATS['Images']:
                    image_destination.mkdir(parents=True, exist_ok=True)
                    await self.move_cd(file, image_destination)
                    self.images += 1
                elif ext in FILE_FORMATS['Videos']:
                    video_destination.mkdir(parents=True, exist_ok=True)
                    await self.move_cd(file, video_destination)
                    self.videos += 1
                else:
                    other_destination.mkdir(parents=True, exist_ok=True)
                    await self.move_cd(file, other_destination)
                    self.other += 1
        await asyncio.sleep(5)
        await purge_dir(self.download_dir)
        await log(f"Organized: {self.audio} Audio Files", style="green")
        await log(f"Organized: {self.images} Image Files", style="green")
        await log(f"Organized: {self.videos} Video Files", style="green")
        await log(f"Organized: {self.other} Other Files", style="green")

    async def move_cd(self, file: Path, dest: Path):
        try:
            dest_file = dest / file.name
            file.rename(dest_file)
        except FileExistsError:
            if file.stat().st_size == dest_file.stat().st_size:
                file.unlink()
                return
            for i in itertools.count(1):
                dest_file = dest / f"{file.stem} ({i}){file.suffix}"
                if not dest_file.is_file():
                    break
            file.rename(dest_file)
