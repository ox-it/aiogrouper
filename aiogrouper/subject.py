__all__ = ['Subject']

class Subject:
    def __init__(self, *, id=None, identifier=None, source=None, name=None, grouper=None):
        assert id or identifier
        self.id = id
        self.identifier, self.source = identifier, source
        self.name = name
        self.grouper = grouper

    @classmethod
    def from_json(cls, value, grouper=None):
        if isinstance(value, dict):
            return cls(id=value['id'],
                       identifier=value.get('identifierLookup'),
                       source=value.get('sourceId'),
                       name=value.get('name'),
                       grouper=grouper)
        elif isinstance(value, cls):
            return value
        raise ValueError

    def to_json(self, lookup=False):
        if lookup:
            data = {}
            if self.id:
                data['subjectId'] = self.id
            if self.identifier:
                data['subjectIdentifier'] = self.identifier
            if self.source:
                data['subjectSourceId'] = self.source
            return data
        data = {'subjectId': self.id}
        return data

    def __str__(self):
        return '<Subject {}: {!r}>'.format(self.id, self.name)
    __repr__ = __str__
