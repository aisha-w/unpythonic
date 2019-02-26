# -*- coding: utf-8 -*-
"""Sequence operations with native slice syntax."""

from ...syntax import macros, fup, view

from itertools import repeat

def test():
    # functional update for sequences
    # (when you want to be more functional than Python allows)
    lst = (1, 2, 3, 4, 5)
    assert fup[lst[3] << 42] == (1, 2, 3, 42, 5)
    assert fup[lst[0::2] << tuple(repeat(10, 3))] == (10, 2, 10, 4, 10)
    assert fup[lst[1::2] << tuple(repeat(10, 3))] == (1, 10, 3, 10, 5)
    assert fup[lst[::2] << tuple(repeat(10, 3))] == (10, 2, 10, 4, 10)
    assert fup[lst[::-1] << tuple(range(5))] == (4, 3, 2, 1, 0)
    assert lst == (1, 2, 3, 4, 5)

    # writable view for sequences
    # (when you want to be more imperative than Python allows)
    lst = [1, 2, 3, 4, 5]
    v = view[lst[2:4]]
    v[:] = [10, 20]
    assert lst == [1, 2, 10, 20, 5]

    lst = [1, 2, 3, 4, 5]
    v = view[lst]
    v[2:4] = [10, 20]
    assert lst == [1, 2, 10, 20, 5]

    print("All tests PASSED")