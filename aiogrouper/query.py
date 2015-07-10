import abc

class Query(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def query_type(self):
        pass

    def to_json(self):
        return {
            'queryFilterType': self.query_type,
        }

    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)

    def __sub__(self, other):
        return Minus(self, other)

class BinaryOperator(Query):
    def __init__(self, left, right):
        self.left, self.right = left, right

    def to_json(self):
        data = super().to_json()
        data.update({'queryFilter0': self.left,
                     'queryFilter1': self.right})

class And(BinaryOperator):
    query_type = 'AND'

class Or(BinaryOperator):
    query_type = 'OR'

class Minus(BinaryOperator):
    query_type = 'MINUS'

class FindByStemName(Query):
    query_type = 'FIND_BY_STEM_NAME'

    def __init__(self, stem_name, recursive=False):
        self.stem_name = stem_name
        self.recursive = recursive

    def to_json(self):
        data = super().to_json()
        data['stemName'] = self.stem_name
        if self.recursive:
            data['stemNameScope'] = 'ALL_IN_SUBTREE'
        return data


