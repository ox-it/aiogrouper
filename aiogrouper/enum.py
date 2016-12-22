import enum

__all__ = ['FieldType', 'StemScope', 'CompositeType', 'PermissionAssignment', 'SaveMode', 'PrivilegeName']


class FieldType(enum.Enum):
    list = 'list'
    access = 'access'
    attribute_def = 'attribute_def'
    naming = 'naming'


class StemScope(enum.Enum):
    one_level = 'ONE_LEVEL'
    all_in_subtree = 'ALL_IN_SUBTREE'


class CompositeType(enum.Enum):
    intersection = 'intersection'
    complement = 'complement'
    union = 'union'


class PermissionAssignment(enum.Enum):
    assign = 'assign_permission'
    remove = 'remove_permission'


class SaveMode(enum.Enum):
    insert = 'INSERT'
    update = 'UPDATE'
    insert_or_update = 'INSERT_OR_UPDATE'


class PrivilegeName(enum.Enum):
    read = 'read'
    view = 'view'
    update = 'update'
    admin = 'admin'
    optin = 'optin'
    optout = 'optout'
    stem = 'stem'
    create = 'create'
    groupAttrRead = 'groupAttrRead'
    groupAttrUpdate = 'groupAttrUpdate'
    stemAttrRead = 'stemAttrRead'
    stemAttrUpdate = 'stemAttrUpdate'


class ResultCode(enum.Enum):
    success_already_existed = 'SUCCESS_ALREADY_EXISTED'
    success = 'SUCCESS'
    success_wasnt_immediate = 'SUCCESS_WASNT_IMMEDIATE'
    subject_not_found = 'SUBJECT_NOT_FOUND'

ResultCode.inverse = {m.value: m for m in ResultCode.__members__.values()}
