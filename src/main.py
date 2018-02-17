# -*- coding: utf-8 -*-

import os
import sys
import json
import pymongo
from pymongo import MongoClient
from collections import Set, Mapping, deque
from numbers import Number
from pymongo import MongoClient

from mongo_initials import *

from collection import Collection
from document import LocalDocument, WebDocument

zero_depth_bases = (str, bytes, Number, range, bytearray)
iteritems = 'items'


def getsize(obj_0):
    """Recursively iterate to sum size of object & members."""
    def inner(obj, _seen_ids=set()):
        obj_id = id(obj)
        if obj_id in _seen_ids:
            return 0
        _seen_ids.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, zero_depth_bases):
            pass # bypass remaining control flow and return
        elif isinstance(obj, (tuple, list, Set, deque)):
            size += sum(inner(i) for i in obj)
        elif isinstance(obj, Mapping) or hasattr(obj, iteritems):
            size += sum(inner(k) + inner(v) for k, v in getattr(obj, iteritems)())
        # Check for custom object instances - may subclass above too
        if hasattr(obj, '__dict__'):
            size += inner(vars(obj))
        if hasattr(obj, '__slots__'): # can have __slots__ with __dict__
            size += sum(inner(getattr(obj, s)) for s in obj.__slots__ if hasattr(obj, s))
        return size
    return inner(obj_0)


if __name__ == '__main__':
    ### Queries ###

    collection = Collection(mdb, mcolls)
    directory = 'documents'

    # Read documents
    for (dirname, _, filenames) in os.walk(directory):
        for filename in filenames:
            d = LocalDocument(os.path.join(dirname, filename))
            collection.read_document(d)

    d = WebDocument('http://www.csd.auth.gr/el/')
    collection.read_document(d)

    collection.flush_to_mongo()
    print('Let\'s go team!')

    # Make query
    q = "Πληροφορικής"
    k = 4
    result = collection.processquery_vector(q, above=0)
    print("\nResults:")
    for d in result:
        #print(d)
        print("{} with: {}".format(d[0], d[1]))
    #print()
    #print(getsize(index.index))

