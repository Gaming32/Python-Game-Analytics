import os
import warnings

import parse
import requests
from requests.compat import urljoin

from game_analytics.common import *


_error_name_patt = parse.compile('<span style="color:darkred">{message}</span>')


class ProfileProxy:
    def __init__(self, client, fields, data):
        self._client = client
        self._field_types = fields
        self._fields = data

    def __getattr__(self, name):
        return self._fields[name]

    def _check_type(self, field_name, value):
        field_types = self._field_types
        if field_name not in field_types:
            return False
        if not isinstance(value, config_data_types[field_types[field_name]]):
            return False
        return True

    def __setattr__(self, name, value):
        if not self._check_type(name, value):
            raise TypeError(f'invalid type for field {name!r}: {type(value).__name__!r}')
        self._fields[name] = value
        self._client._push('profile', {'field': name, 'value': value})


class AnalyticsClient:
    def __init__(self, server_url='http://localhost:26259', userid=None, cache_dir='analytics'):
        self.server_url = server_url
        self.userid = userid
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        self.autosave = False
        self._profile = None

    def _get_url(self, rel):
        return urljoin(self.server_url, rel)

    def _get_cache_path(self, rel):
        return os.path.join(self.cache_dir, rel)

    def load_userid(self):
        file_path = self._get_cache_path('userid')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='ascii') as fp:
                self.userid = fp.read()

    def save_userid(self):
        file_path = self._get_cache_path('userid')
        if self.userid is not None:
            with open(file_path, 'w', encoding='ascii') as fp:
                fp.write(self.userid)

    def autosave_userid(self):
        if self.userid is None:
            self.load_userid()
        self.autosave = True

    def close(self):
        if self.autosave:
            self.save_userid()

    def _push(self, endpoint: str, data: dict):
        data = data.copy()
        data['endpoint'] = endpoint
        data['id'] = self.userid
        requests.post(self._get_url('/push'), json=data)

    def get_profile(self) -> ProfileProxy:
        if self._profile is None:
            user_data_resp = requests.get(self._get_url('/pull'), json={
                'endpoint': 'profile',
                'id': self.userid
            })
            if user_data_resp.status_code == 404:
                return None
            user_data = user_data_resp.json()
            self.userid = user_data.pop('id')
            field_types = requests.get(self._get_url('/get-profile-fields')).json()
            newprof = ProfileProxy(self, field_types, user_data)
            self._profile = newprof
        return self._profile

    @property
    def profile(self) -> ProfileProxy:
        if self._profile is None:
            warnings.warn('profile property accessed before get_profile or new_profile called', UserWarning)
        return self.get_profile()

    @staticmethod
    def _error(klass, resp):
        error_parsed = _error_name_patt.search(resp.text)
        message = error_parsed.named.get('message')
        raise klass(message)

    def new_profile(self, **fields) -> ProfileProxy:
        user_data_resp = requests.get(self._get_url('/new-user'), json=fields)
        if user_data_resp.status_code == 400:
            self._error(ValueError, user_data_resp)
        user_data = user_data_resp.json()
        self.userid = user_data.pop('id')
        field_types = requests.get(self._get_url('/get-profile-fields')).json()
        newprof = ProfileProxy(self, field_types, user_data)
        self._profile = newprof
        return newprof
