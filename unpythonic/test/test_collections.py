# -*- coding: utf-8 -*-

from collections.abc import Mapping, MutableMapping, Hashable, Container, Iterable, Sized
from pickle import dumps, loads

from ..collections import box, frozendict, view, roview, ShadowedSequence, mogrify

def test():
    # box: mutable single-item container à la Racket
    b = box(17)
    def f(b):
        b.x = 23
    assert b.x == 17
    f(b)
    assert b.x == 23

    b2 = box(17)
    assert 17 in b2
    assert 23 not in b2
    assert [x for x in b2] == [17]
    assert b2 == 17  # for convenience, a box is considered equal to the item it contains
    assert len(b2) == 1
    assert b2 != b

    b3 = box(17)
    assert b3 == b2  # boxes are considered equal if their contents are

    try:
        d = {}
        d[b] = "foo"
    except TypeError:
        pass
    else:
        assert False, "box should not be hashable"

    assert not issubclass(box, Hashable)
    assert issubclass(box, Container)
    assert issubclass(box, Iterable)
    assert issubclass(box, Sized)

    b1 = box("abcdefghijklmnopqrstuvwxyzåäö")
    b2 = loads(dumps(b1))  # pickling
    assert b2 == b1

    # frozendict: like frozenset, but for dictionaries
    d3 = frozendict({'a': 1, 'b': 2})
    assert d3['a'] == 1
    try:
        d3['c'] = 42
    except TypeError:
        pass
    else:
        assert False, "frozendict should not be writable"

    d4 = frozendict(d3, a=42)  # functional update
    assert d4['a'] == 42 and d4['b'] == 2
    assert d3['a'] == 1  # original not mutated

    d5 = frozendict({'a': 1, 'b': 2}, {'a': 42})  # rightmost definition of each key wins
    assert d5['a'] == 42 and d5['b'] == 2

    assert frozendict() is frozendict()  # empty-frozendict singleton property

    d7 = frozendict({1:2, 3:4})
    assert 3 in d7
    assert len(d7) == 2
    assert set(d7.keys()) == {1, 3}
    assert set(d7.values()) == {2, 4}
    assert set(d7.items()) == {(1, 2), (3, 4)}
    assert d7 == frozendict({1:2, 3:4})
    assert d7 != frozendict({1:2})
    assert d7 == {1:2, 3:4}  # like frozenset, __eq__ doesn't care whether mutable or not
    assert d7 != {1:2}
    assert {k for k in d7} == {1, 3}
    assert d7.get(3) == 4
    assert d7.get(5, 0) == 0
    assert d7.get(5) is None

    assert issubclass(frozendict, Mapping)
    assert not issubclass(frozendict, MutableMapping)

    assert issubclass(frozendict, Hashable)
    assert hash(d7) == hash(frozendict({1:2, 3:4}))
    assert hash(d7) != hash(frozendict({1:2}))

    assert issubclass(frozendict, Container)
    assert issubclass(frozendict, Iterable)
    assert issubclass(frozendict, Sized)

    d1 = frozendict({1: 2, 3: 4, "somekey": "somevalue"})
    d2 = loads(dumps(d1))  # pickling
    assert d2 == d1

    # writable live view for sequences
    # (when you want to be more imperative than Python allows)
    lst = list(range(5))
    v = view(lst)
    lst[2] = 10
    assert v == [0, 1, 10, 3, 4]
    assert v[2:] == [10, 3, 4]
    assert v[2] == 10
    assert v[::-1] == [4, 3, 10, 1, 0]
    assert tuple(reversed(v)) == (4, 3, 10, 1, 0)
    assert 10 in v
    assert 42 not in v
    assert [x for x in v] == [0, 1, 10, 3, 4]
    assert len(v) == 5
    assert v.index(10) == 2
    assert v.count(10) == 1
    assert v[:] is v

    # views may be created also of slices (note the syntax: the subscripting is curried)
    lst = list(range(10))
    v = view(lst)[2:]
    assert v == [2, 3, 4, 5, 6, 7, 8, 9]
    v2 = v[:-2]  # slicing a view returns a new view
    assert v2 == [2, 3, 4, 5, 6, 7]
    v[3] = 20
    v2[2] = 10
    assert lst == [0, 1, 2, 3, 10, 20, 6, 7, 8, 9]

    lst = list(range(10))
    v = view(lst)[::2]
    assert v == [0, 2, 4, 6, 8]
    v2 = v[1:-1]
    assert v2 == [2, 4, 6]
    v2[1:] = (10, 20)
    assert lst == [0, 1, 2, 3, 10, 5, 20, 7, 8, 9]

    lst[2] = 42
    assert v == [0, 42, 10, 20, 8]
    assert v2 == [42, 10, 20]

    # supports in-place reverse
    lst = list(range(5))
    v = view(lst)
    v.reverse()
    assert lst == [4, 3, 2, 1, 0]

    lst = list(range(5))
    v = view(lst)
    v[2] = 10
    assert lst == [0, 1, 10, 3, 4]

    lst = list(range(5))
    v = view(lst)
    v[2:4] = (10, 20)
    assert lst == [0, 1, 10, 20, 4]

    lst = list(range(5))
    v = view(lst)[2:4]
    v[:] = (10, 20)
    assert lst == [0, 1, 10, 20, 4]
    assert v[-1] == 20

    # writing a scalar value into a slice broadcasts it, à la NumPy
    lst = list(range(5))
    v = view(lst)[2:4]
    v[:] = 42
    assert lst == [0, 1, 42, 42, 4]

    # we store slice specs, not actual indices, so it doesn't matter if the
    # underlying sequence undergoes length changes
    lst = list(range(5))
    v = view(lst)[2:]
    assert v == [2, 3, 4]
    lst.append(5)
    assert v == [2, 3, 4, 5]
    lst.insert(0, 42)
    assert v == [1, 2, 3, 4, 5]
    assert lst == [42, 0, 1, 2, 3, 4, 5]

    # read-only live view for sequences
    # useful to give read access to an internal sequence
    lst = list(range(5))
    v = roview(lst)[2:]
    assert v == [2, 3, 4]
    lst.append(5)
    assert v == [2, 3, 4, 5]  # it's live
    assert type(v[1:]) is roview  # slicing a read-only view gives another read-only view
    assert v[1:] == [3, 4, 5]
    try:
        view(v[1:])
    except TypeError:
        pass
    else:
        assert False, "should not be able to create a writable view into a read-only view"
    try:
        v[2] = 3
    except TypeError:
        pass
    else:
        assert False, "read-only view should not support item assignment"
    try:
        v.reverse()
    except AttributeError:  # no such method
        pass
    else:
        assert False, "read-only view should not support in-place reverse"

    # sequence shadowing
    tpl = (1, 2, 3, 4, 5)
    s = ShadowedSequence(tpl, 2, 42)
    assert s == (1, 2, 42, 4, 5)
    assert tpl == (1, 2, 3, 4, 5)
    assert s[2:] == (42, 4, 5)

    s2 = ShadowedSequence(tpl, slice(2, 4), (23, 42))
    assert s2 == (1, 2, 23, 42, 5)
    assert tpl == (1, 2, 3, 4, 5)
    assert s2[2:] == (23, 42, 5)
    assert s2[::-1] == (5, 42, 23, 2, 1)

    s3 = ShadowedSequence(tpl)
    assert s3 == tpl

    s4 = ShadowedSequence(s2, slice(3, 5), (100, 200))
    assert s4 == (1, 2, 23, 100, 200)
    assert s2 == (1, 2, 23, 42, 5)
    assert tpl == (1, 2, 3, 4, 5)

     # in-place map
    double = lambda x: 2*x
    lst = [1, 2, 3]
    lst2 = mogrify(double, lst)
    assert lst2 == [2, 4, 6]
    assert lst2 is lst

    s = {1, 2, 3}
    s2 = mogrify(double, s)
    assert s2 == {2, 4, 6}
    assert s2 is s

    # mogrifying a dict mutates its values in-place, leaving keys untouched
    d = {1: 2, 3: 4, 5: 6}
    d2 = mogrify(double, d)
    assert set(d2.items()) == {(1, 4), (3, 8), (5, 12)}
    assert d2 is d

    # dict keys/items/values types cannot be instantiated, and support only
    # iteration (not in-place modification), so in those cases mogrify()
    # returns a new set without mutating the dict's bindings.
    # (But any side effects of func will be applied to each item, as usual,
    #  so the items themselves may change if they are mutable.)
    d = {1: 2, 3: 4, 5: 6}
    assert mogrify(double, d.items()) == {(2, 4), (6, 8), (10, 12)}  # both keys and values get mogrified!
    assert mogrify(double, d.keys()) == {2, 6, 10}
    assert mogrify(double, d.values()) == {4, 8, 12}
    assert d == {1: 2, 3: 4, 5: 6}

    b = box(17)
    b2 = mogrify(double, b)
    assert b2 == 34
    assert b2 is b

    tup = (1, 2, 3)
    tup2 = mogrify(double, tup)
    assert tup2 == (2, 4, 6)
    assert tup2 is not tup  # immutable, cannot be updated in-place

    fs = frozenset({1, 2, 3})
    fs2 = mogrify(double, fs)
    assert fs2 == {2, 4, 6}
    assert fs2 is not fs

    fd = frozendict({1: 2, 3: 4})
    fd2 = mogrify(double, fd)
    assert set(fd2.items()) == {(1, 4), (3, 8)}
    assert fd2 is not fd

    atom = 17
    atom2 = mogrify(double, atom)
    assert atom2 == 34
    assert atom2 is not atom

    # mogrify a sequence through a mutable view
    lst = [1, 2, 3]
    v = view(lst)[1:]
    v2 = mogrify(double, v)
    assert v2 == [4, 6]
    assert lst == [1, 4, 6]

    # mogrify a copy of a sequence through a read-only view
    lst = [1, 2, 3]
    v = roview(lst)[1:]
    v2 = mogrify(double, v)
    assert v2 == [4, 6]
    assert lst == [1, 2, 3]

    print("All tests PASSED")

if __name__ == '__main__':
    test()
