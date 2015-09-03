__all__ = ['Subject', 'Subjectlike', 'SubjectLookup']

class Subjectlike(object):
    pass

class Subject(Subjectlike):
    def __init__(self, id, identifier=None, source=None, name=None):
        self.id = id
        self.identifier, self.source = identifier, source
        self.name = name

    @classmethod
    def coerce(cls, value):
        if isinstance(value, dict):
            return cls(id=value['id'],
                       identifier=value.get('identifierLookup'),
                       source=value.get('sourceId'),
                       name=value.get('name'))
        elif isinstance(value, cls):
            return value
        raise ValueError

    def as_json(self):
        data = {'subjectId': self.id}
        return data

    def __str__(self):
        return '<Subject {}: {!r}>'.format(self.id, self.name)
    __repr__ = __str__

class SubjectLookup(Subjectlike):
    def __init__(self, identifier, source=None):
        self.identifier, self.source = identifier, source

    def as_json(self):
        data = {'subjectIdentifier': self.identifier}
        if self.source:
            data['subjectSource'] = self.source
        return data

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        else:
            raise ValueError
