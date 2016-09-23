class Membership:
    def __init__(self, grouper, id, target, subject, direct, created):
        self.grouper, self.id = grouper, id
        self.target, self.subject = target, subject
        self.direct, self.created = direct, created

    def __repr__(self):
        return '<Membership {!r} in {!r}>'.format(self.subject, self.target)