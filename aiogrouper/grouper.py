import asyncio
import collections
import collections.abc
import json
from urllib.parse import urljoin

import aiohttp

from .enum import FieldType, StemScope, SaveMode, PrivilegeName
from .exceptions import api_exceptions, GrouperAPIException
from .group import Group, GroupToSave
from .query import Query
from .stem import Stem, StemToSave
from .subject import Subject
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
        return urljoin(self._base_url, 'servicesRest/v2_2_000/')

    @property
    def stems_url(self):
        return urljoin(self.api_url, 'stems')

    @property
    def groups_url(self):
        return urljoin(self.api_url, 'groups')

    @property
    def group_members_url(self):
        return urljoin(self.api_url, 'groups/{}/members')

    @property
    def memberships_url(self):
        return urljoin(self.api_url, 'memberships')

    @property
    def privileges_url(self):
        return urljoin(self.api_url, 'grouperPrivileges')

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
        return self.parse_response(data, response_data)

    @asyncio.coroutine
    def get(self, path):
        return (yield from self.request('get', path, None))

    @asyncio.coroutine
    def post(self, path, data):
        return (yield from self.request('post', path, data))

    @asyncio.coroutine
    def put(self, path, data):
        return (yield from self.request('put', path, data))

    def parse_response(self, input, data):
        results_name, data = data.popitem()

        if data['resultMetadata']['success'] == 'F':
            exc = api_exceptions.get(data['resultMetadata']['resultCode'], GrouperAPIException)
            raise exc(data['resultMetadata']['resultMessage'], input, data)

        if results_name == 'WsHasMemberResults':
            results = {}
            for result in data['results']:
                results[Subject.from_json(result['wsSubject'])] = tf_to_bool(result['resultMetadata']['success'])
            return results
        elif results_name == 'WsGetMembershipsResults':
            groups = {g['uuid']: Group.from_json(g, grouper=self) for g in data.get('wsGroups', ())}
            subjects = {g['id']: Subject.from_json(g, grouper=self) for g in data.get('wsSubjects', ())}
            results = collections.defaultdict(set)
            for membership in data.get('wsMemberships', ()):
                results[subjects[membership['subjectId']]].add(groups[membership['groupId']])
            return dict(results)
        elif results_name == 'WsGroupSaveResults':
            return [Group.from_json(r['wsGroup'], grouper=self) for r in data['results']]
        elif results_name == 'WsStemSaveResults':
            return [Stem.from_json(r['wsStem'], grouper=self) for r in data['results']]
        elif results_name == 'WsGetMembersLiteResult':
            return [Subject.from_json(g, grouper=self) for g in data.get('wsSubjects', ())]
        elif results_name == 'WsGetGrouperPrivilegesLiteResult':
            results = collections.defaultdict(set)
            subjects = {}
            for privilege in data['privilegeResults']:
                subject_key = (privilege['wsSubject']['sourceId'], privilege['wsSubject']['id'])
                if subject_key not in subjects:
                    subjects[subject_key] = Subject.from_json(privilege['wsSubject'], self)
                results[subjects[subject_key]].add(PrivilegeName[privilege['privilegeName']])
            return dict(results)
        else:
            return data

    @asyncio.coroutine
    def add_members(self, group, members, *, replace_existing=False):
        assert isinstance(group, Group)
        assert all(isinstance(m, Subject) for m in members)

        url = self.group_members_url.format(group.name)
        data = {
            'WsRestAddMemberRequest': {
                'replaceAllExisting': bool_to_tf(replace_existing),
                'subjectLookups': [member.to_json() for member in members],
            },
        }
        return (yield from self.put(url, data))

    @asyncio.coroutine
    def delete_members(self, group, members):
        assert isinstance(group, Group)
        assert all(isinstance(m, Subject) for m in members)

        url = self.group_members_url.format(group.name)
        data = {
            'WsRestDeleteMemberRequest': {
                'subjectLookups': [member.to_json() for member in members],
            },
        }
        return (yield from self.put(url, data))

    @asyncio.coroutine
    def set_members(self, group, members):
        return (yield from self.add_members(group, members,
                                            replace_existing=True))

    @asyncio.coroutine
    def get_members(self, group):
        assert isinstance(group, Group)
        return (yield from self.get(self.group_members_url.format(group.name)))

    @asyncio.coroutine
    def find_groups(self, *, groups=None, query=None):
        assert isinstance(query, Query) or all(isinstance(g, Group) for g in groups)
        data = {}
        if query:
            data['wsQueryFilter'] = query.to_json()
        elif groups:
            data['wsGroupLookups'] = [g.to_json(lookup=True) for g in groups]
        data = {'WsRestFindGroupsRequest': data}
        return (yield from self.post(self.groups_url, data))

    @asyncio.coroutine
    def find_stems(self, *, lookups=None, query=None):
        data = {
            'WsRestFindStemsRequest': {}
        }
        if lookups is not None:
            assert isinstance(lookups, collections.abc.Iterable)
            assert all(isinstance(l, Stem) for l in lookups)
            assert query is None
            data['WsRestFindStemsRequest']['wsStemLookups'] = [l.to_json(lookup=True) for l in lookups]
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
    def get_memberships(self, members, *,
                        groups=None,
                        subject_attribute_names=(),
                        stem=None,
                        stem_scope=StemScope.all_in_subtree,
                        field_type=None):
        if groups is not None and len(groups) == 0:
            return {member: set() for member in members}
        assert all(isinstance(member, Subject) for member in members)
        data = {
            'WsRestGetMembershipsRequest': {
                'subjectAttributeNames': list(subject_attribute_names),
                'memberFilter': 'All',
                'includeGroupDetail': 'F',
                'includeSubjectDetail': 'F',
                'wsSubjectLookups': [m.to_json(lookup=True) for m in members],
            }
        }
        if groups is not None:
            assert all(isinstance(group, Group) for group in groups)
            data['WsRestGetMembershipsRequest']['wsGroupLookups'] = [g.to_json(lookup=True) for g in groups]
        if stem is not None:
            assert isinstance(stem, Stem)
            data['WsRestGetMembershipsRequest']['wsStemLookup'] = stem.to_json(lookup=True)
            data['WsRestGetMembershipsRequest']['stemScope'] = stem_scope.value
        if field_type is not None:
            assert isinstance(field_type, FieldType)
            data['WsRestGetMembershipsRequest']['fieldType'] = field_type.value

        return (yield from self.post(self.memberships_url, data))

    @asyncio.coroutine
    def get_subject_memberships(self, member, groups=None, subject_attribute_names=()):
        results = yield from self.get_memberships([member], groups, subject_attribute_names)
        return results.popitem()[1]

    @asyncio.coroutine
    def has_members(self, group, members):
        assert isinstance(group, Group)
        assert all(isinstance(member, Subject) for member in members)
        data = {
            'WsRestHasMemberRequest': {
                'subjectLookups': [m.to_json(lookup=True) for m in members],
            }
        }
        return (yield from self.post(self.group_members_url.format(group.name), data))

    @asyncio.coroutine
    def has_member(self, group, member):
        results = yield from self.has_members(group, [member])
        return results.popitem()[1]

    @asyncio.coroutine
    def save_groups(self, group_to_saves, save_mode=SaveMode.insert_or_update):
        assert all(isinstance(g, (Group, GroupToSave)) for g in group_to_saves)
        group_to_saves = [g if isinstance(g, GroupToSave) else GroupToSave(g, save_mode=save_mode)
                          for g in group_to_saves]
        data = {'WsRestGroupSaveRequest': {
            'wsGroupToSaves': [g.to_json() for g in group_to_saves],
        }}
        groups = (yield from self.put(self.groups_url, data))
        group_map = {g.name: g for g in groups}
        for group_to_save in group_to_saves:
            if group_to_save.group_lookup.name in group_map:
                group_to_save.group.uuid = group_map[group_to_save.group_lookup.name].uuid
                group_to_save.group.name = group_map[group_to_save.group_lookup.name].name
        return groups

    @asyncio.coroutine
    def save_group(self, group):
        return (yield from self.save_groups([group]))[0]

    @asyncio.coroutine
    def save_stems(self, stem_to_saves, save_mode=SaveMode.insert_or_update):
        assert all(isinstance(s, (Stem, StemToSave)) for s in stem_to_saves)
        data = {'WsRestStemSaveRequest': {
            'wsStemToSaves': [s.to_json()
                              if isinstance(s, StemToSave) else
                              StemToSave(s, save_mode=save_mode).to_json()
                              for s in stem_to_saves]
        }}
        return (yield from self.put(self.stems_url, data))

    @asyncio.coroutine
    def save_stem(self, stem):
        return (yield from self.save_stems([stem]))[0]

    @asyncio.coroutine
    def assign_privileges(self, privilege_names, allowed=True,
                          stem=None, group=None, members=(),
                          replace_existing=False):
        assert all(isinstance(pn, PrivilegeName) for pn in privilege_names)
        data = {
            'allowed': bool_to_tf(allowed),
            'privilegeType': 'access' if group else 'naming',
            'privilegeNames': [pn.value for pn in privilege_names],
        }
        if members:

            data['wsSubjectLookups'] = [m.to_json(lookup=True) for m in members]
        if stem:
            data['wsStemLookup'] = stem.to_json(lookup=True)
        if group:
            data['wsGroupLookup'] = group.to_json(lookup=True)

        data = {'WsRestAssignGrouperPrivilegesRequest': data}
        return (yield from self.post(self.privileges_url, data))

    def get_privileges(self, *,
                       stem=None, group=None, subject=None,
                       privilege_name=None):
        assert isinstance(stem, Stem) or isinstance(group, Group)
        assert subject is None or isinstance(subject, Subject)
        assert privilege_name is None or isinstance(privilege_name, PrivilegeName)
        data = {
            'privilegeType': 'access' if group else 'naming',
        }
        if stem: data['stemName'] = stem.name
        elif group: data['groupName'] = group.name
        if subject and subject.id: data['subjectId'] = subject.id
        if subject and subject.identifier: data['subjectIdentifier'] = subject.identifier
        if subject and subject.source: data['subjectSourceId'] = subject.source
        data = {'WsRestGetGrouperPrivilegesLiteRequest': data}
        result = (yield from self.post(self.privileges_url, data))
        if subject:
            return result.popitem()[1] if result else set()
        else:
            return result
