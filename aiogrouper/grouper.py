import asyncio
import collections
import collections.abc
import http
import json
import logging
import time
from urllib.parse import urljoin

import aiohttp

from .attribute import Attribute
from .membership import Membership
from .enum import FieldType, StemScope, SaveMode, PrivilegeName, ResultCode
from .exceptions import api_exceptions, GrouperAPIException, GrouperDeserializeException, GrouperHTTPException, \
    ProblemDeletingGroups, ProblemDeletingStems
from .group import Group, GroupToSave
from .query import Query, FindByStemName, FindByParentStemName
from .stem import Stem, StemToSave
from .subject import Subject
from .util import tf_to_bool, bool_to_tf

__all__ = ['Grouper', 'Stem', 'Group', 'Attribute', 'Membership']

logger = logging.getLogger('aiogrouper')


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

    @property
    def attribute_assignments_url(self):
        return urljoin(self.api_url, 'attributeAssignments')

    @asyncio.coroutine
    def request(self, method, path, data):
        headers = {'Content-Type': 'text/x-json'}
        url = urljoin(self._base_url, path)
        if hasattr(data, 'to_json'):
            data = data.to_json()
        if isinstance(data, dict):
            data = json.dumps(data)
        start_time = time.time()
        response = yield from self._session.request(method, url,
                                                    data=data,
                                                    headers=headers)
        duration = int((time.time() - start_time) * 1000)
        try:
            if response.status not in (http.client.OK, http.client.CREATED, http.client.INTERNAL_SERVER_ERROR):
                response_data = yield from response.read()
                logger.error("Grouper exception: %s %s %s %s %s %s",
                             method, url, response.status, dict(response.headers), data, response_data)
                raise GrouperHTTPException(response, response_data)
            response_data = yield from response.json()
        finally:
            response.close()
        logger.debug("Grouper request: %s %s %s %dms", method, url, response.status, duration,
                     extra={'responseHeaders': dict(response.headers),
                            'requestBody': data,
                            'responseBody': response_data})
        return self.parse_response(method, path, data, response_data)

    @asyncio.coroutine
    def get(self, path):
        return (yield from self.request('get', path, None))

    @asyncio.coroutine
    def post(self, path, data):
        return (yield from self.request('post', path, data))

    @asyncio.coroutine
    def put(self, path, data):
        return (yield from self.request('put', path, data))

    def parse_response(self, method, path, input, output, ignore_error=False):
        results_name, data = next(iter(output.items()))

        if not ignore_error and data['resultMetadata']['success'] == 'F':
            exc = api_exceptions.get(data['resultMetadata']['resultCode'], GrouperAPIException)
            raise exc(data['resultMetadata']['resultMessage'], method, path, input, output)

        if results_name == 'WsHasMemberResults':
            results = {}
            for result in data['results']:
                results[Subject.from_json(result['wsSubject'])] = tf_to_bool(result['resultMetadata']['success'])
            return results
        elif results_name == 'WsGetMembershipsResults':
            groups = {g['uuid']: Group.from_json(g, grouper=self) for g in data.get('wsGroups', ())}
            stems = {g['uuid']: Stem.from_json(g, grouper=self) for g in data.get('wsStems', ())}
            subjects = {g['id']: Subject.from_json(g, grouper=self) for g in data.get('wsSubjects', ())}
            results = collections.defaultdict(set)
            for membership in data.get('wsMemberships', ()):
                if 'groupId' in membership:
                    results[subjects[membership['subjectId']]].add(groups[membership['groupId']])
                else:
                    results[subjects[membership['subjectId']]].add(stems[membership['ownerStemId']])
            return dict(results)
        elif results_name == 'WsFindStemsResults':
            return [Stem.from_json(r, grouper=self) for r in data['stemResults']]
        elif results_name == 'WsFindGroupsResults':
            return [Group.from_json(r, grouper=self) for r in data.get('groupResults', ())]
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
        elif results_name == 'WsAssignGrouperPrivilegesResults':
            return data
        elif results_name == 'WsGroupDeleteResults':
            pass # TODO
        elif results_name == 'WsStemDeleteResults':
            pass # TODO
        elif results_name in ('WsAddMemberResults', 'WsDeleteMemberResults'):
            results = collections.OrderedDict()
            for result in data['results']:
                results[Subject.from_json(result['wsSubject'])] = \
                    ResultCode.inverse[result['resultMetadata']['resultCode']] if result['wsSubject']['id'] != 'None' else ResultCode.subject_not_found
            return results
        else:
            raise GrouperDeserializeException("Don't know how to deserialize response of type {}".format(results_name))

    @asyncio.coroutine
    def add_members(self, group, members, *, replace_existing=False):
        members = list(members)
        if not members:
            if replace_existing:
                yield from self.clear_members(group)
            return collections.OrderedDict()
        assert isinstance(group, Group)
        assert all(isinstance(m, Subject) for m in members)
        subject_lookups = [member.to_json(lookup=True) for member in members]
        if not subject_lookups:
            return collections.OrderedDict()
        url = self.group_members_url.format(group.name)
        data = {
            'WsRestAddMemberRequest': {
                'replaceAllExisting': bool_to_tf(replace_existing),
                'subjectLookups': subject_lookups,
            },
        }
        return (yield from self.put(url, data))

    @asyncio.coroutine
    def delete_members(self, group, members):
        members = list(members)
        assert isinstance(group, Group)
        assert all(isinstance(m, Subject) for m in members)
        subject_lookups = [member.to_json(lookup=True) for member in members]
        if not subject_lookups:
            return collections.OrderedDict()
        url = self.group_members_url.format(group.name)
        data = {
            'WsRestDeleteMemberRequest': {
                'subjectLookups': subject_lookups,
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
    def delete_groups(self, groups):
        if not groups:
            return {}
        assert all(isinstance(group, Group) for group in groups)
        data = {'WsRestGroupDeleteRequest': {
            'wsGroupLookups': [group.to_json(lookup=True) for group in groups]
        }}
        try:
            return (yield from self.post(self.groups_url, data))
        except ProblemDeletingGroups as e:
            return self.parse_response(e.method, e.path, e.input, e.output,
                                       ignore_error=True)

    @asyncio.coroutine
    def delete_stems(self, stems):
        if not stems:
            return {}
        assert all(isinstance(stem, Stem) for stem in stems)
        data = {'WsRestStemDeleteRequest': {
            'wsStemLookups': [stem.to_json(lookup=True) for stem in stems]
        }}
        try:
            return (yield from self.post(self.stems_url, data))
        except ProblemDeletingStems as e:
            return self.parse_response(e.method, e.path, e.input, e.output,
                                       ignore_error=True)

    @asyncio.coroutine
    def find_stems(self, *, lookups=None, query=None):
        data = {}
        if lookups is not None:
            assert all(isinstance(l, Stem) for l in lookups)
            assert query is None
            data['wsStemLookups'] = [l.to_json(lookup=True) for l in lookups]
            if not data['wsStemLookups']:
                return []
        elif query is not None:
            assert isinstance(query, Query)
            data['wsStemQueryFilter'] = query.to_json(stem_query=True)
        else:
            raise AssertionError("Must provide either lookups or query")
        data = {'WsRestFindStemsRequest': data}
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
    def get_subject_memberships(self, member, *,
                                groups=None,
                                subject_attribute_names=(),
                                stem=None,
                                stem_scope=StemScope.all_in_subtree,
                                field_type=None):
        results = yield from self.get_memberships([member],
                                                  groups=groups,
                                                  subject_attribute_names=subject_attribute_names,
                                                  stem=stem,
                                                  stem_scope=stem_scope,
                                                  field_type=field_type)
        try:
            return results.popitem()[1]
        except KeyError:
            return set()

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
        stems = (yield from self.put(self.stems_url, data))
        stem_map = {s.name: s for s in stems}
        for stem_to_save in stem_to_saves:
            if stem_to_save.stem_lookup.name in stem_map:
                stem_to_save.stem.uuid = stem_map[stem_to_save.stem_lookup.name].uuid
                stem_to_save.stem.name = stem_map[stem_to_save.stem_lookup.name].name
        return stems

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
                       privilege_name=None,
                       include_group_detail=False,
                       include_subject_detail=False):
        assert isinstance(stem, Stem) or isinstance(group, Group)
        assert subject is None or isinstance(subject, Subject)
        assert privilege_name is None or isinstance(privilege_name, PrivilegeName)
        data = {
            'privilegeType': 'access' if group else 'naming',
            'includeGroupDetail': bool_to_tf(include_group_detail),
            'includeSubjectDetail': bool_to_tf(include_subject_detail),
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

    @asyncio.coroutine
    def assign_attributes(self, somethings, attributes, values):
        somethings_by_type = collections.defaultdict(list)

        if not isinstance(somethings, collections.Container):
            somethings = [somethings]
        if not isinstance(attributes, collections.Container):
            attributes = [attributes]
        if not all(isinstance(attribute, Attribute) for attribute in attributes):
            raise TypeError("All attributes must be Attribute instances")

        for something in somethings:
            for cls in (Group, Stem, Membership, Subject):
                if isinstance(something, cls):
                    somethings_by_type[cls].append(something)
                    break
            else:
                raise TypeError('{!r} not of suitable type {!r}'.format(something, type(something)))

        for cls, somethings in somethings_by_type.items():
            name = cls.__name__
            data = {
                'WsRestAssignAttributesRequest': {
                    'attributeAssignOperation': 'assign_attr',
                    'attributeAssignType': name.lower(),
                    'wsAttributeDefNameLookups': list(attribute.to_json(lookup=True) for attribute in attributes),
                    'wsOwner{}Lookups'.format(name): list(something.to_json(lookup=True) for something in somethings),
                    'values': [{'valueSystem': value} for value in values],
                },
            }
            result = (yield from self.post(self.attribute_assignments_url, data))

    @asyncio.coroutine
    def recursive_delete(self, stem, include_sub_stems=True, include_base_stem=False):
        groups = yield from self.find_groups(query=FindByStemName(stem.name, recursive=True))
        results = yield from self.delete_groups(groups)
        if include_sub_stems:
            stems = yield from self.find_stems(query=FindByParentStemName(stem.name))
            if include_base_stem:
                stems.append(stem)
            yield from self.delete_stems(stems)
