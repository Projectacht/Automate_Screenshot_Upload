import re

from asu.upload import BaseHost, UploadRange, UploadedFile
from asu.modules import requests


class Host(BaseHost):
    quantity = UploadRange(1, 20)  # Upper bound is arbitrary

    thumbnail_sizes = (100, 150, 200, 250, 300, 350)
    thumbnail_size = 200

    def __init__(self, username=None, password=None, thumbnail_size=None):
        self.username = username
        self.password = password

        if thumbnail_size:
            self.thumbnail_size = thumbnail_size

        self.uploaded_files = []

    def upload(self, files):
        base_url = 'http://someimage.com/'
        upload_url = base_url + 'upload.php'
        retrieve_url = base_url + 'done'

        sess = requests.session()

        if (self.username, self.password) != (None, None):
            login_url = base_url + 'index.php'
            data = {'act': 'takelogin',
                    'username': self.username,
                    'password': self.password}

            resp = sess.post(login_url, data=data)
            assert resp.status_code == requests.codes.ok
        else:
            assert sess.get(base_url).status_code == requests.codes.ok

        data = {'name': None,  # set in loop
                'safe': '1',
                'thumb': 'w' + str(self.thumbnail_size),
                'gallery': '1',
                'galleryname': ''}

        uploaded_names = []
        for count, f in enumerate(files, 1):
            data['name'] = 'image{:02}.png'.format(count)

            open_file = None
            if isinstance(f, str):
                upfile = open_file = open(f, 'rb')
                uploaded_names.append(f)
            else:
                upfile = f
                uploaded_names.append(getattr(f, 'name', None) or data['name'])

            try:
                data_files = (('file', (data['name'], upfile)),)

                resp = sess.post(upload_url, data=data, files=data_files)

                assert resp.status_code == requests.codes.ok
            finally:
                if open_file:
                    open_file.close()

        resp = sess.get(retrieve_url)

        self._html = resp.text

        uploaded = []
        for fn, (pu, tu) in zip(uploaded_names, self._get_links(resp.text)):
            uploaded.append(UploadedFile(fn, pu, tu))

        self.uploaded_files += uploaded

        return uploaded

    @staticmethod
    def _get_links(html):
        """return a list of tuples, each tuple containing the image page link
           and the direct link to the thumbnail file"""

        regex = (r'\[URL=(http://[^\]]*)\]\[IMG\](http://[^\[]*)'
                 r'\[/IMG\]\[/URL\]')
        return re.findall(regex, html)
