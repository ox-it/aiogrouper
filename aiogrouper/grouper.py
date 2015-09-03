import asyncio
import collections
import collections.abc
import json
from urllib.parse import urljoin

import aiohttp

from .group import Group, Grouplike
from .query import Query
from .stem import StemLookup
from .subject import Subject, Subjectlike
from .util import tf_to_bool, bool_to_tf

__all__ = ['Grouper']

class Grouper(object):
    def __init__(self, base_url, session=None):
        self._base_url = base_url
        self._session = session or aiohttp.ClientSession()

    def close(self):
        self._session.close()

    @property
    def api_url(self):
        return urljoin(self._base_url, 'servicesRest/v2_1_005/')

    @property
    def stems_url(self):
        return urljoin(self.api_url, 'stems/')

    @property
    def groups_url(self):
        return urljoin(self.api_url, 'groups/')

    @property
    def group_members_url(self):
        return urljoin(self.api_url, 'groups/{}/members')

    @property
    def memberships_url(self):
        return urljoin(self.api_url, 'memberships')

    @asyncio.coroutine
    def request(self, method, path, data):
        headers = {'Content-Type': 'text/x-json'}
        url = urljoin(self._base_url, path)
        if hasattr(data, 'to_json'):
            data = data.to_json()
        if isinstance(data, dict):
            data = json.dumps(data)
        response = yield from self._session.request(method, url,
                                                    data=data,
                                                    headers=headers)
        response_data = yield from response.json()
        response.close()
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


    def parse_response(self, data):
        if 'WsHasMemberResults' in data:
            results = {}
            for result in data['WsHasMemberResults']['results']:
                results[Subject.coerce(result['wsSubject'])] = tf_to_bool(result['resultMetadata']['success'])
            return results
        elif 'WsGetMembershipsResults' in data:
            groups = {g['uuid']: Group.coerce(g) for g in data['WsGetMembershipsResults']['wsGroups']}
            subjects = {g['id']: Subject.coerce(g) for g in data['WsGetMembershipsResults']['wsSubjects']}
            results = collections.defaultdict(set)
            for membership in data['WsGetMembershipsResults']['wsMemberships']:
                results[subjects[membership['subjectId']]].add(groups[membership['groupId']])
            return dict(results)
        else:
            return data

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
    def find_stems(self, *, lookups=None, query=None):
        data = {
            'WsRestFindStemsRequest': {}
        }
        if lookups is not None:
            assert isinstance(lookups, collections.abc.Iterable)
            assert all(isinstance(l, StemLookup) for l in lookups)
            assert query is None
            data['WsRestFindStemsRequest']['wsStemLookups'] = [l.to_json() for l in lookups]
            if not data['WsRestFindStemsRequest']['wsStemLookups']:
                return None
        elif query is not None:
            assert isinstance(query, Query)
            data['WsRestFindStemsRequest']['wsStemQueryFilter'] = query.to_json()
        else:
            raise AssertionError("Must provide either lookups or query")
        return (yield from self.post(self.stems_url, data))

    @asyncio.coroutine
    def lookup_groups(self, groups):
        data = {
            'WsRestFindGroupsRequest': {
                'wsGroupLookups': query.to_json(),
            },
        }
        return (yield from self.post(self.groups_url, data))

    @asyncio.coroutine
    def get_memberships(self, members, groups=None, subject_attribute_names=()):
        if groups is not None and len(groups) == 0:
            return {member: set() for member in members}
        assert all(isinstance(member, Subjectlike) for member in members)
        data = {
            'WsRestGetMembershipsRequest': {
                'subjectAttributeNames': list(subject_attribute_names),
                'memberFilter': 'All',
                'includeGroupDetail': 'F',
                'includeSubjectDetail': 'F',
                'wsSubjectLookups': [m.to_json() for m in members],
            }
        }
        if groups is not None:
            assert all(isinstance(group, Grouplike) for group in groups)
            data['WsRestGetMembershipsRequest']['wsGroupLookups'] = [g.to_json() for g in groups]
        return (yield from self.post(self.memberships_url, data))

    @asyncio.coroutine
    def get_subject_memberships(self, member, groups=None, subject_attribute_names=()):
        results = yield from self.get_memberships([member], groups, subject_attribute_names)
        return results.popitem()[1]

    @asyncio.coroutine
    def has_members(self, group, members):
        assert isinstance(group, Grouplike)
        assert all(isinstance(member, Subjectlike) for member in members)
        data = {
            'WsRestHasMemberRequest': {
                'subjectLookups': [m.to_json() for m in members],
            }
        }
        return (yield from self.post(self.group_members_url.format(group.name), data))

    @asyncio.coroutine
    def has_member(self, group, member):
        results = yield from self.has_members(group, [member])
        return results.popitem()[1]


