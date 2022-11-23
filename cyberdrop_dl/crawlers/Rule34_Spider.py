from xml.etree.ElementTree import Element
from yarl import URL

from ..base_functions.base_functions import log, logger
from ..base_functions.data_classes import DomainItem
from ..client.client import Session


class Rule34Crawler:
    def __init__(self, *, include_id=False, quiet: bool):
        self.include_id = include_id
        self.quiet = quiet

    async def fetch(self, session: Session, url: URL):
        try:
            # get the &id=1234 part from the url
            # an url can look like this:
            # https://rule34.xxx/index.php?page=post&s=view&id=6766683
            id = url.query['id']

            # call the api for
            # https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&id=${OUR_ID}
            apiUrl = URL("https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&id=" + id)
            response = await session.get_xml(apiUrl)

            for child in response:
                if child.tag != "post":
                    continue
                file_url = child.attrib["file_url"]
                break

            domain_object = DomainItem("rule34.xxx", {})
            await domain_object.add_to_album("Rule34", URL(file_url), url)
            
            return domain_object

        except Exception as e:
            logger.debug("Error encountered while handling %s", str(url), exc_info=True)
            await log("Error scraping " + str(url), quiet=self.quiet)
            logger.debug(e)
