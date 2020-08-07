import collections
from copy import deepcopy

def merge(dict1, dict2):
    """ Return a new dictionary by merging two dictionaries recursively. """

    result = deepcopy(dict1)

    for key, value in dict2.items():
        if isinstance(value, collections.abc.Mapping):
            result[key] = merge(result.get(key, {}), value)
        else:
            result[key] = deepcopy(dict2[key])

    return result

def find_keys(node, kv):
    """Returns all the keys matching kv in a given node/dict"""

    if isinstance(node, list):
        for i in node:
            for x in find_keys(i, kv):
               yield x
    elif isinstance(node, dict):
        if kv in node:
            yield node[kv]
        for j in node.values():
            for x in find_keys(j, kv):
                yield x

def enum_values(node):
    """Returns all the values in a given dict/node"""

    if isinstance(node, list):
        for i in node:
            for x in enum_values(i):
               yield x
    elif isinstance(node, dict):
        for j in node.values():
            for x in enum_values(j):
                yield x
    else:
        yield node

def enum_keys(node):
    """Returns all the keys in a given dict/node"""
    
    if isinstance(node, list):
        for i in node:
            for x in enum_keys(i):
               yield x
    elif isinstance(node, dict):
        for j in node.keys():
            yield j
            for x in enum_keys(node[j]):
                yield x                        

def sub_dict(somedict, somekeys, default=None):
    """Return just the given keys from a dict"""

    return dict([ (k, somedict.get(k, default)) for k in somekeys ])

def dict_match(query_dict, target_dict):
    """Determine if the target_dict contains the keys/values in the query_dict"""

    query_keys=list(enum_keys(query_dict))
    if sub_dict(target_dict,query_keys)==query_dict:
        return True
    else:
        return False