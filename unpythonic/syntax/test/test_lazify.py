# -*- coding: utf-8 -*-
"""Automatic lazy evaluation of function arguments."""

from ...misc import raisef

from ...syntax import macros, lazify

from macropy.quick_lambda import macros, lazy

from macropy.tracing import macros, show_expanded

def test():
#    with show_expanded:
    # in a "with lazify" block, function arguments are evaluated only when actually used.
    with lazify:
        # basic usage
        def my_if(p, a, b):
            if p:
                return a  # b never evaluated in this code path
            else:
                return b  # a never evaluated in this code path

        # basic test for argument passing/returns
        assert my_if(True, 23, 0) == 23
        assert my_if(False, 0, 42) == 42

        # test the laziness
        # note the raisef() calls; in regular Python, they'd run anyway before my_if() gets control.
        assert my_if(True, 23, raisef(RuntimeError, "I was evaluated!")) == 23
        assert my_if(False, raisef(RuntimeError, "I was evaluated!"), 42) == 42

        # In this example, the divisions by zero are never performed.
        assert my_if(True, 23, 1/0) == 23
        assert my_if(False, 1/0, 42) == 42

        # named args
        def my_if2(*, test, then, otherwise):
            if test:
                return then
            else:
                return otherwise
        assert my_if2(test=True, then=23, otherwise=1/0) == 23
        assert my_if2(test=False, then=1/0, otherwise=42) == 42

        # starargs
        def foo(*args):
            return args
        # case 1: pass as regular positional args
        assert foo(1, 2, 3) == (1, 2, 3)
        # case 2: pass a literal tuple of computations as *args
        assert foo(*(2+2, 2+3, 3+3)) == (4, 5, 6)
        # case 3: pass already computed data as *args
        t = (4, 5, 6)
        assert foo(*t) == (4, 5, 6)

        # accessing only part of starargs (at the receiving end)
        def foo2(*args):
            return args[0]
        assert foo2(42, 1/0, 1/0) == 42
        assert foo2(*(42, 1/0, 1/0)) == 42
        def foo3(*args):
            return args[:-1]
        assert foo3(23, 42, 1/0) == (23, 42)
        assert foo3(*(23, 42, 1/0)) == (23, 42)

        # kwargs
        def bar(**dic):
            return dic["a"], dic["b"]
        # case 1: pass as regular named args
        assert bar(a="tavern", b="pub") == ("tavern", "pub")
        # case 2: pass a literal dict of computations as **kwargs
        assert bar(**{"a": ("tav"+"ern"), "b": ("p"+"ub")}) == ("tavern", "pub")
        # case 3: pass already computed data as **kwargs
        d = {"a": "tavern", "b": "pub"}
        assert bar(**d) == ("tavern", "pub")

        # accessing only part of kwargs (at the receiving end)
        assert bar(a=1, b=2, c=1/0) == (1, 2)
        assert bar(**{"a": 1, "b": 2, "c": 1/0}) == (1, 2)

        # CAUTION: overwriting a formal with a new value needs a manual lazy[],
        # to honor the contract that formal parameter names refer to promises.
        def f(x):
            x = lazy[2*21]
            assert x == 42  # auto-evaluated because "x" is the name of a formal

            x = 17  # DANGER! NO! ("x" originally referred to a formal parameter)
            try:
                print(x)
            except TypeError:  # int is not callable
                pass
            else:
                assert False, "int should not be callable"
        f(17)

        def g(x):
            y = x  # this auto-evaluates due to the read on the RHS
            assert y == 42  # y is just a value
            assert x == 42  # auto-evaluated (now cached value) since "x" is the original name
        g(2*21)

    print("All tests PASSED")