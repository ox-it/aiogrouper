class GrouperException(Exception):
    pass


class GrouperDeserializeException(GrouperException):
    pass


class GrouperHTTPException(GrouperException):
    def __init__(self, response, body):
        self.message = 'HTTP exception: {}'.format(response.status)
        self.response = response
        self.body = body


class GrouperAPIException(GrouperException):
    result_code = 'EXCEPTION'

    def __init__(self, message, method, path, input, output):
        self.method, self.path = method, path
        self.input, self.output = input, output
        super().__init__(message)

    def __str__(self):
        return "<{} {} {} {} {}>".format(type(self).__name__,
                                         self.method, self.path,
                                         self.input, self.output)


class ProblemSavingStems(GrouperAPIException):
    result_code = 'PROBLEM_SAVING_STEMS'


class ProblemDeletingGroups(GrouperAPIException):
    result_code = 'PROBLEM_DELETING_GROUPS'


class ProblemDeletingStems(GrouperAPIException):
    result_code = 'PROBLEM_DELETING_STEMS'


api_exceptions = {}
_locals = dict(locals())
for obj in _locals.values():
    if isinstance(obj, type) and issubclass(obj, GrouperAPIException):
        api_exceptions[obj.result_code] = obj