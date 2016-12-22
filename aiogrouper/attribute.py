from .stem import Stem


class Attribute(Stem):
    def to_json(self, lookup=False):
        if lookup:
            if self.name:
                return {'name': self.name}
            elif self.uuid:
                return {'uuid': self.uuid}
        return super().to_json(lookup)
