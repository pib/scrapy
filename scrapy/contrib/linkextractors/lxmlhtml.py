"""
Link extractor based on lxml.html
"""

import lxml.html

from scrapy.link import Link
from scrapy.utils.python import unique as unique_list
import collections

class LxmlParserLinkExtractor(object):
    def __init__(self, tag="a", attr="href", process=None, unique=False):
        self.scan_tag = tag if isinstance(tag, collections.Callable) else lambda t: t == tag
        self.scan_attr = attr if isinstance(attr, collections.Callable) else lambda a: a == attr
        self.process_attr = process if isinstance(process, collections.Callable) else lambda v: v
        self.unique = unique

        self.links = []

    def _extract_links(self, response_text, response_url):
        html = lxml.html.fromstring(response_text)
        html.make_links_absolute(response_url)
        for e, a, l, p in html.iterlinks():
            if self.scan_tag(e.tag):
                if self.scan_attr(a):
                    link = Link(self.process_attr(l), text=e.text)
                    self.links.append(link)

        links = unique_list(self.links, key=lambda link: link.url) \
                if self.unique else self.links

        return links

    def extract_links(self, response):
        return self._extract_links(response.body, response.url)


