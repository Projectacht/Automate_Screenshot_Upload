import re

from asu.upload import BaseHost, UploadRange, UploadedFile
from asu.modules import requests


class Host(BaseHost):
    quantity = UploadRange(1, 20)

    thumbnail_sizes = (100, 150, 180, 250, 300, 350)
    thumbnail_size = 180

    def __init__(self, username=None, password=None, thumbnail_size=None):
        self.username = username
        self.password = password

        if thumbnail_size:
            self.thumbnail_size = thumbnail_size

        self.uploaded_files = []

    def upload(self, files):
        sess = requests.session()

        if (self.username, self.password) != (None, None):
            url = 'http://www.imagebam.com/login'
            data = {'action': 'true', 'nick': self.username,
                    'pw': self.password}
            resp = sess.post(url, data=data)
            assert resp.status_code == requests.codes.ok

        url = 'http://www.imagebam.com/sys/upload/save'
        data = {'content_type': '0',
                'thumb_size': self.thumbnail_size,
                'thumb_aspect_ratio': 'resize',
                'thumb_file_type': 'jpg',
                'gallery_options': '1',
                'galley_title': '',
                'galley_description': ''}

        data_files = []
        opened_files = []
        uploaded_names = []
        try:  # finally close the files that were opened
            for count, f in enumerate(files, 1):
                upload_name = 'image{:02}.png'.format(count)

                if isinstance(f, str):
                    open_file = open(f, 'rb')
                    opened_files.append(open_file)

                    uploaded_names.append(f)
                else:
                    open_file = f

                    filename = getattr(f, 'name', None) or upload_name
                    uploaded_names.append(filename)

                data_files.append(('file[]', (upload_name, open_file)))

            resp = sess.post(url, data=data, files=data_files)
            assert resp.status_code == requests.codes.ok

            self._html = resp.text
        finally:
            for open_file in opened_files:
                open_file.close()

        uploaded = []
        for fn, (pu, tu) in zip(uploaded_names, self._get_links(self._html)):
            uploaded.append(UploadedFile(fn, pu, tu))

        self.uploaded_files += uploaded

        return uploaded

    @staticmethod
    def _get_links(html):
        """return a list of tuples, each tuple containing the image page link
           and the direct link to the thumbnail file"""

        regex = (r'value=\'\[URL=(http://[^\]]*)\]\[IMG\](http://[^\[]*)'
                 r'\[/IMG\]\[/URL\]')
        return re.findall(regex, html)
