import asyncio

from .enum import CompositeType

__all__ = ['Group', 'CompositeGroup']


class Group:
    def __init__(self, name=None, uuid=None, display_extension=None, grouper=None, **kwargs):
        assert name or uuid
        self.name = name
        self.uuid = uuid
        self.display_extension = display_extension
        self.grouper = grouper

    @classmethod
    def from_json(cls, data, grouper):
        if data.get('hasComposite') == 'T':
            return CompositeGroup.from_json(data, grouper)
        return cls(display_extension=data.get('displayExtension'),
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

    @asyncio.coroutine
    def save(self):
        group = (yield from (self.grouper.save_group(self)))
        self.uuid = group.uuid

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

    @classmethod
    def from_json(cls, data, grouper):
        return cls(display_extension=data.get('displayExtension'),
                   name=data.get('name'),
                   uuid=data.get('uuid'),
                   composite_type=CompositeType[data['compositeType']],
                   left=data['leftGroup'],
                   right=data['rightGroup'],
                   grouper=grouper)