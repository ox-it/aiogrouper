import asyncio
from aiogrouper.util import bool_to_tf
from aiogrouper.enum import SaveMode

__all__ = ['Stem', 'StemToSave']


class Stem:
    def __init__(self, grouper, *, name=None, uuid=None,
                 description=None, extension=None, display_extension=None):
        assert name or uuid, "One of name and uuid must be provided"
        self.name = name
        self.uuid = uuid
        self.description = description
        self.extension = extension
        self.display_extension = display_extension
        self.grouper = grouper
    
    def to_json(self, lookup=False):
        if lookup:
            if self.name:
                return {'stemName': self.name}
            elif self.uuid:
                return {'uuid': self.uuid}

        data = {}
        if self.name:
            data['name'] = self.name
        if self.uuid:
            data['uuid'] = self.uuid
        if self.description:
            data['description'] = self.description
        if self.display_extension:
            data['displayExtension'] = self.display_extension
        return data

    @classmethod
    def from_json(cls, data, grouper=None):
        return cls(name=data.get('name'),
                   uuid=data.get('uuid'),
                   extension=data.get('extension'),
                   display_extension=data.get('displayExtension'),
                   description=data.get('description'),
                   grouper=grouper)

    @asyncio.coroutine
    def save(self, **kwargs):
        return (yield from self.grouper.save_stem(StemToSave(self, **kwargs)))


class StemToSave(object):
    def __init__(self, stem, *,
                 stem_lookup=None,
                 save_mode=SaveMode.insert_or_update,
                 create_parent_stems_if_not_exist=False):
        self.stem = stem
        self.stem_lookup = stem_lookup or stem
        self.save_mode = save_mode
        self.create_parent_stems_if_not_exist = create_parent_stems_if_not_exist

    def to_json(self):
        return {
            'wsStem': self.stem.to_json(),
            'wsStemLookup': self.stem_lookup.to_json(lookup=True),
            'saveMode': self.save_mode.value,
            'createParentStemsIfNotExist': bool_to_tf(self.create_parent_stems_if_not_exist),
        }
