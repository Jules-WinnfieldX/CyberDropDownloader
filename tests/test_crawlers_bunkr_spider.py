import unittest
from yarl import URL

from cyberdrop_dl.crawlers.Bunkr_Spider import BunkrCrawler

# Run with: python3 -m unittest ./tests/test_crawlers_bunkr_spider.py
class TestBunkrCrawler(unittest.TestCase):
    def assertExpectedURL(self, origURL, newURL):
        self.assertEqual(BunkrCrawler.get_stream_link(URL(origURL)), URL(newURL))

    def test_get_stream_link_no_extension(self):
        """Test that URLs with an unknown extension are returned without changing
        """
        self.assertExpectedURL("https://bunkr.ru/unknown-GT2Awd69m", "https://bunkr.ru/unknown-GT2Awd69m")
        self.assertExpectedURL("https://bunkrr.su/unknown-GT2Awd69m", "https://bunkrr.su/unknown-GT2Awd69m")

    def test_get_stream_link_other_extension(self):
        """Test that URLs with an extension other than video, audio, and image are changed correctly
        """
        self.assertExpectedURL("https://c.bunkr.ru/doc-GT2Awd69m.txt", "https://bunkrr.su/d/doc-GT2Awd69m.txt")
        self.assertExpectedURL("https://media-files7.bunkr.ru/doc-GT2Awd69m.txt", "https://bunkrr.su/d/doc-GT2Awd69m.txt")

    def test_get_stream_link_caps_extension(self):
        """Test that URLs with a capital file extension are changed correctly
        """
        self.assertExpectedURL("https://cdn.bunkr.ru/vid-GT2Awd69m.MP4", "https://bunkrr.su/v/vid-GT2Awd69m.MP4")
        self.assertExpectedURL("https://cdn9.bunkrr.su/vid-GT2Awd69m.MP4", "https://bunkrr.su/v/vid-GT2Awd69m.MP4")

    def test_get_stream_link_image_extension(self):
        """Test that URLs with an image file extension are changed correctly

        Image URLs do not have their domain updated except for changing "cdn" to "i" in the first part of the hostname
        """
        self.assertExpectedURL("https://cdn5.bunkr.la/pic-GT2Awd69m.jpg", "https://i5.bunkr.la/pic-GT2Awd69m.jpg")
        self.assertExpectedURL("https://i5.bunkr.la/pic-GT2Awd69m.jpg", "https://i5.bunkr.la/pic-GT2Awd69m.jpg")
        self.assertExpectedURL("https://i.bunkr.ru/pic-GT2Awd69m.jpg", "https://i.bunkr.ru/pic-GT2Awd69m.jpg")
        self.assertExpectedURL("https://cdn9.bunkrr.su/pic-GT2Awd69m.JPG", "https://i9.bunkrr.su/pic-GT2Awd69m.JPG")

    def test_get_stream_link_video_extension(self):
        """Test that URLs with a video extension are changed correctly
        """
        self.assertExpectedURL("https://c9.bunkrr.su/vid-GT2Awd69m.mp4", "https://bunkrr.su/v/vid-GT2Awd69m.mp4")
        self.assertExpectedURL("https://c9.bunkr.ru/vid-GT2Awd69m.mp4", "https://bunkrr.su/v/vid-GT2Awd69m.mp4")
        self.assertExpectedURL("https://bunkrr.su/v/vid-GT2Awd69m.mp4", "https://bunkrr.su/v/vid-GT2Awd69m.mp4")
        self.assertExpectedURL("https://media-files9.bunkr.is/vid-GT2Awd69m.mp4", "https://bunkrr.su/v/vid-GT2Awd69m.mp4")
        self.assertExpectedURL("https://bunkrr.su/v/vid-GT2Awd69m.mp4", "https://bunkrr.su/v/vid-GT2Awd69m.mp4")

if __name__ == '__main__':
    unittest.main()
