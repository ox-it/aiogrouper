__all__ = ['Group', 'Grouplike']

class Grouplike(object):
    pass

class Group(Grouplike):
    def __init__(self, name=None, uuid=None, display_extension=None, **kwargs):
        assert name or uuid
        self.name = name
        self.uuid = uuid
        self.display_extension = display_extension

    @classmethod
    def coerce(cls, value):
        if isinstance(value, dict):
            return cls(display_extension=value.get('displayExtension'),
                       name=value.get('name'),
                       uuid=value.get('uuid'))
        return cls(name=value)

    def to_json(self):
        data = {}
        if self.name:
            data['groupName'] = self.name
        if self.uuid:
            data['uuid'] = self.uuid
        return data

    def __eq__(self, other):
        return (self.name == other.name) if self.name else \
               (self.uuid == other.uuid) if self.uuid else False

    def __hash__(self):
        return (hash(self.__class__) << 2) ^ (hash(self.name) << 1) ^ hash(self.uuid)

    def __str__(self):
        return '<Group {}: {!r}>'.format(self.name or self.uuid, self.display_extension)
    __repr__ = __str__
