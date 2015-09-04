class StemLookup():
    def __init__(self, *, name=None, uuid=None):
        assert name or uuid, "One of name and uuid must be provided"
        self.name = name
        self.uuid = uuid
    
    def to_json(self):
        data = {}
        if self.name:
            data['stemName'] = self.name
        if self.uuid:
            data['uuid'] = self.uuid
        return data