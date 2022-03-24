from typing import Union

from gofile import Gofile


class GofileCrawler():
    def __init__(self, **kwargs):
        self.client = Gofile()
        self.links: list[str] = kwargs.get("links", [])

    def build_targets(self, targets={}, **kwargs):
        links = kwargs.get("links", self.links)
        for link in links:
            content_id = link.split("/")[-1] if link.startswith("https://gofile.io/") else link
            content = self.client.get_content(content_id)
            if not content:
                continue

            title = content["name"]
            targets[title] = []
            contents: dict[str, dict[str, Union[str, int]]] = content["contents"]
            for val in contents.values():
                if val["type"] == "folder":
                    self.build_targets(targets, links=[val["code"]])
                else:
                    targets[title].append([
                        val["link"] if val["link"] != "overloaded" else val["directLink"],
                        'https://gofile.io/',
                    ])
        return targets
