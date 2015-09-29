import abc

__all__ = ['Query', 'BinaryOperator', 'And', 'Or', 'Minus', 'FindByStemName']


class Query(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def query_type(self):
        pass

    def to_json(self, stem_query=False):
        if stem_query:
            return {'stemQueryFilterType': self.query_type}
        else:
            return {'queryFilterType': self.query_type}

    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)

    def __sub__(self, other):
        return Minus(self, other)


class BinaryOperator(Query):
    def __init__(self, left, right):
        self.left, self.right = left, right

    def to_json(self, **kwargs):
        data = super().to_json(**kwargs)
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

    def to_json(self, **kwargs):
        data = super().to_json(**kwargs)
        data['stemName'] = self.stem_name
        data['stemNameScope'] = 'ALL_IN_SUBTREE' if self.recursive else 'ONE_LEVEL'
        return data


class FindByParentStemName(Query):
    query_type = 'FIND_BY_PARENT_STEM_NAME'

    def __init__(self, parent_stem_name):
        self.parent_stem_name = parent_stem_name

    def to_json(self, **kwargs):
        data = super().to_json(**kwargs)
        data['parentStemName'] = self.parent_stem_name
        return data
