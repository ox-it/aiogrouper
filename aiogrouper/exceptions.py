class GrouperException(Exception):
    pass


class GrouperAPIException(GrouperException):
    def __init__(self, message, input, output):
        self.input = input
        self.output = output
        super().__init__(message)


class ProblemSavingStems(GrouperAPIException):
    result_code = 'PROBLEM_SAVING_STEMS'


api_exceptions = {}
_locals = dict(locals())
for obj in _locals.values():
    if isinstance(obj, type) and issubclass(obj, GrouperAPIException) and obj != GrouperAPIException:
        api_exceptions[obj.result_code] = obj