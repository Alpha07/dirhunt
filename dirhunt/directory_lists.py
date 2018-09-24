import re

from bs4 import NavigableString, Tag

from dirhunt.url import full_url_address, Url


DATETIME_PATTERN = re.compile('(\d{4}-\d{2}-\d{2} +\d{2}:\d{2}(:?\:\d{2}|))')
FILESIZE_PATTERN = re.compile('([\d]+\.?[\d]{0,3} ?[ptgmkb]i?b?)', re.IGNORECASE)


def is_link(element):
    return isinstance(element, Tag) and element.name == 'a'


class DirectoryListBase(object):
    def __init__(self, processor):
        """

        :type processor: ProcessIndexOfRequest
        """
        self.processor = processor

    @classmethod
    def is_applicable(cls, request, text, crawler_url, soup):
        raise NotImplementedError

    def get_links(self, text, soup=None):
        raise NotImplementedError


class ApacheDirectoryList(DirectoryListBase):

    @classmethod
    def is_applicable(cls, request, text, crawler_url, soup):
        return soup.find('pre') and soup.select_one('pre > a') and soup.find('a', href='?C=N;O=D')

    def get_links(self, text, soup=None):
        """
        soup.find('pre').contents

        <class 'list'>: [<img alt="Icon " src="/__apache/blank.gif"/>, ' ',
        <a href="?C=N;O=D">Name</a>, '\n    ',
        <a href="?C=M;O=A">Last modified</a>, '      ',
        <a href="?C=S;O=A">Size</a>, '  \n    ',
        <a href="?C=D;O=A">Description</a>, <hr/>, '\n    ',
        <img alt="[PARENTDIR]" src="/__ovh_icons/back.gif"/>, ' ', <a href="/">Parent Directory</a>, '                             -   \n    ',
        <img alt="[DIR]" src="/__apache/folder.gif"/>, ' ',
        <a href="ID3/">ID3/</a>, '                    2015-09-15 14:58    -   \n    ',
        <img alt="[DIR]" src="/__apache/folder.gif"/>, ' ',
        <a href="IXR/">IXR/</a>, '                    2018-02-16 14:29    -   \n    ',
        <img alt="[   ]" src="/__apache/unknown.gif"/>, ' ',
        <a href="author-template.php">author-template.php</a>, '     \n    2018-02-16 14:29   16K  \n    ',
        <img alt="[   ]" src="/__apache/unknown.gif"/>, ' ',
        <a href="bookmark-template.php">bookmark-template.php</a>, '   \n    2018-02-16 14:29   11K  \n    ']

        :param text:
        :param soup:
        :return:
        """
        contents = list(filter(lambda x: isinstance(x, NavigableString) or is_link(x),
                               soup.find('pre').contents))
        links = []
        for i, content in enumerate(contents):
            if not is_link(content):
                continue
            link = Url(full_url_address(content.attrs.get('href'), self.processor.crawler_url.url))
            if i+1 < len(contents) and isinstance(contents[i+1], NavigableString):
                extra = {}
                text = str(contents[i+1])
                dt = DATETIME_PATTERN.findall(text)
                if dt:
                    extra['created_at'] = dt[0]
                size = FILESIZE_PATTERN.findall(text)
                if size:
                    extra['filesize'] = size[0]
                link.add_extra(extra)
                if link.url.endswith('/'):
                    self.processor.add_url(link, type='directory')
            links.append(link)
        return links


class CommonDirectoryList(DirectoryListBase):
    @classmethod
    def is_applicable(cls, request, text, crawler_url, soup):
        return True

    def get_links(self, text, soup=None):
        links = [full_url_address(link.attrs.get('href'), self.processor.crawler_url.url)
                 for link in soup.find_all('a')]
        for link in filter(lambda x: x.url.endswith('/'), links):
            self.processor.add_url(link, type='directory')
        return [Url(link) for link in links]