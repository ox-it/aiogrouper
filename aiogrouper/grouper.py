import asyncio

import aiohttp

from .group import Group
from .query import Query
from .subject import SubjectLookup

class Grouper(object):
    def __init__(self, base_url, auth):
        self._base_url = base_url
        self._session = aiohttp.ClientSession()

    @property
    def api_url(self):
        return urljoin(self._base_url, 'servicesRest/v2_1_005/')

    @property
    def groups_url(self):
        return urljoin(self.api_url, 'stems/')

    @property
    def groups_url(self):
        return urljoin(self.api_url, 'groups/')

    @property
    def group_members_url(self):
        return urljoin(self.api_url, 'groups/{}/members')

    @asyncio.coroutine
    def request(self, method, path, data):
        headers = {'Content-Type': 'application/json'}
        url = urljoin(self._base_url, path)
        if hasattr(data, 'to_json'):
            data = data.to_json()
        if isinstance(data, dict):
            data = json.dumps(data)
        response = yield from self._session.request(method, url,
                                                    data=data,
                                                    headers=headers)
        response_data = yield from response.json()
        return self.parse_response(response_data)

    @asyncio.coroutine
    def get(self, path):
        return (yield from self.request('get', path, None))

    @asyncio.coroutine
    def post(self, path, data):
        return (yield from self.request('post', path, data))

    @asyncio.coroutine
    def put(self, path, data):
        return (yield from self.request('put', path, data))


    def parse_response(self, response_data):
        return response_data

    @asyncio.coroutine
    def add_members(self, group, members, *, replace_existing=False):
        group = Group.coerce(group)
        members = [SubjectLookup.coerce(member) for member in members]

        url = self.group_members_url.format(group.name)
        data = {
            'WsRestAddMemberRequest': {
                'replaceAllExisting': bool_to_str(replace_existing),
                'subjectLookups': [member.to_json() for member in members],
            },
        }

        return (yield from self.put(url, data))

    @asyncio.coroutine
    def set_members(self, group, members):
        return (yield from self.add_members(group, members,
                                            replace_existing=replace_existing))

    @asyncio.coroutine
    def find_groups(self, query):
        assert isinstance(query, Query)
        data = {
            'WsRestFindGroupsRequest': {
                'wsQueryFilter': query.to_json(),
            },
        }
        return (yield from self.post(self.groups_url, data))

    @asyncio.coroutine
    def find_stems(self, query):
        assert isinstance(query, Query)
        data = {
            'WsRestFindStemsRequest': {
                'wsStemQueryFilter': query.to_json(),
            },
        }
        return (yield from self.post(self.stems_url, data))

    @asyncio.coroutine
    def lookup_groups(self, groups):
        data = {
            'WsRestFindGroupsRequest': {
                'wsGroupLookups': query.to_json(),
            },
        }
        return (yield from self.post(self.groups_url, data))

