import asyncio

from .subject import Subject

from .util import bool_to_tf
from .enum import CompositeType, SaveMode

__all__ = ['Group', 'CompositeGroup', 'GroupToSave']


class Group:
    def __init__(self, grouper, name=None, uuid=None,
                 extension=None, display_extension=None, **kwargs):
        assert name or uuid
        self.grouper = grouper
        self.name = name
        self.uuid = uuid
        self.extension = extension
        self.display_extension = display_extension

    @classmethod
    def from_json(cls, data, grouper):
        if data.get('hasComposite') == 'T':
            return CompositeGroup.from_json(data, grouper)
        return cls(display_extension=data.get('displayExtension'),
                   extension=data.get('extension'),
                   name=data.get('name'),
                   uuid=data.get('uuid'),
                   grouper=grouper)

    def to_json(self, lookup=False):
        if lookup:
            if self.name:
                return {'groupName': self.name}
            elif self.uuid:
                return {'uuid': self.uuid}
        data = {}
        if self.name:
            data['name'] = self.name
        if self.uuid:
            data['uuid'] = self.uuid
        if self.display_extension:
            data['displayExtension'] = self.display_extension
        return data

    def as_subject(self):
        return Subject(identifier=self.name, source='g:gsa')

    @asyncio.coroutine
    def save(self, **kwargs):
        return (yield from self.grouper.save_group(GroupToSave(self, **kwargs)))

    def __eq__(self, other):
        return (self.name == other.name) if self.name else \
               (self.uuid == other.uuid) if self.uuid else False

    def __hash__(self):
        return (hash(self.__class__) << 2) ^ (hash(self.name) << 1) ^ hash(self.uuid)

    def __str__(self):
        return '<Group {}: {!r}>'.format(self.name or self.uuid, self.display_extension)
    __repr__ = __str__


class CompositeGroup(Group):
    def __init__(self, *, composite_type, left, right, **kwargs):
        self.composite_type = composite_type
        self.left, self.right = left, right
        super().__init__(**kwargs)

    def to_json(self):
        data = super().to_json()
        data.update({
            'hasComposite': 'T',
            'compositeType': self.composite_type.value,
            'leftGroup': self.left.to_json(),
            'rghtGroup': self.right.to_json(),
        })
        return data

    def as_subject(self):
        return Subject(identifier=self.name, source='g:gsa',
                       name=self.display_extension)

    @classmethod
    def from_json(cls, data, grouper):
        return cls(display_extension=data.get('displayExtension'),
                   name=data.get('name'),
                   uuid=data.get('uuid'),
                   composite_type=CompositeType[data['compositeType']],
                   left=data['leftGroup'],
                   right=data['rightGroup'],
                   grouper=grouper)


class GroupToSave(object):
    def __init__(self, group, *,
                 group_lookup=None,
                 save_mode=SaveMode.insert_or_update,
                 create_parent_stems_if_not_exist=False):
        self.group = group
        self.group_lookup = group_lookup or group
        self.save_mode = save_mode
        self.create_parent_stems_if_not_exist = create_parent_stems_if_not_exist

    def to_json(self):
        return {
            'wsGroup': self.group.to_json(),
            'wsGroupLookup': self.group_lookup.to_json(lookup=True),
            'saveMode': self.save_mode.value,
            'createParentStemsIfNotExist': bool_to_tf(self.create_parent_stems_if_not_exist),
        }
