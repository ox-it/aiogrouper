import enum


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
