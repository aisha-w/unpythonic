#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Missing batteries for functools."""

__all__ = ["memoize", "curry", "flip",
           "foldl", "foldr", "reducel", "reducer",
           "composer1", "composel1",
           "composer", "composel", "to1st", "to2nd", "tokth", "tolast", "to"]

from functools import wraps, partial
from operator import itemgetter

from unpythonic.arity import arities

def memoize(f):
    """Decorator: memoize the function f.

    All of the args and kwargs of ``f`` must be hashable.

    Any exceptions raised by ``f`` are also memoized. If the memoized function
    is invoked again with arguments with which ``f`` originally raised an
    exception, *the same exception instance* is raised again.

    **CAUTION**: ``f`` must be pure (no side effects, no internal state
    preserved between invocations) for this to make any sense.
    """
    success, fail = [object() for _ in range(2)]  # sentinels
    memo = {}
    @wraps(f)
    def memoized(*args, **kwargs):
        k = (args, tuple(sorted(kwargs.items(), key=itemgetter(0))))
        if k not in memo:
            try:
                result = (success, f(*args, **kwargs))
            except BaseException as err:
                result = (fail, err)
            memo[k] = result  # should yell separately if k is not a valid key
        sentinel, value = memo[k]
        if sentinel is fail:
            raise value
        else:
            return value
    return memoized

def curry(f):
    """Decorator: curry the function f.

    Essentially, the resulting function automatically chains partial application
    until the minimum positional arity of ``f`` is satisfied, at which point
    ``f``is called.

    Also more kwargs can be passed at each step, but they do not affect the
    decision when the function is called.

    Examples::

        @curry
        def add3(a, b, c):
            return a + b + c
        assert add3(1)(2)(3) == 6

        @curry
        def lispyadd(*args):
            return sum(args)
        assert lispyadd() == 0  # no args is a valid arity here

        @curry
        def foo(a, b, *, c, d):
            return a, b, c, d
        assert foo(5, c=23)(17, d=42) == (5, 17, 23, 42)
    """
    # TODO: improve: all required name-only args should be present before calling f.
    # Difficult, partial() doesn't remove an already-set kwarg from the signature.
    min_arity, _ = arities(f)
    @wraps(f)
    def curried(*args, **kwargs):
        if len(args) < min_arity:
            return curry(partial(f, *args, **kwargs))
        return f(*args, **kwargs)
    return curried

def flip(f):
    """Decorator: flip (reverse) the positional arguments of f."""
    @wraps(f)
    def flipped(*args, **kwargs):
        return f(*reversed(args), **kwargs)
    return flipped

def foldl(proc, init, sequence0, *sequences):  # minimum arity should be 3
    """Racket-like foldl that supports multiple input sequences.

    At least one sequence (``sequence0``) is required. More are optional.

    Terminates when the shortest sequence runs out.

    Initial value is mandatory; there is no sane default for the case with
    multiple input sequences.

    Note order: ``proc(elt, acc)``, which is the opposite order of arguments
    compared to ``functools.reduce``. General case ``proc(e1, ..., en, acc)``.
    """
    sequences = (sequence0,) + sequences
    if not sequences:
        raise TypeError("Need at least one sequence")
    def heads(its):
        hs = []
        for it in its:
            try:
                h = next(it)
            except StopIteration:  # shortest sequence ran out
                return StopIteration
            hs.append(h)
        return tuple(hs)
    iters = tuple(iter(s) for s in sequences)
    acc = init
    while True:
        hs = heads(iters)
        if hs is StopIteration:
            return acc
        acc = proc(*(hs + (acc,)))

def foldr(proc, init, sequence0, *sequences):
    """Like foldl, but fold from the right (walk each sequence backwards)."""
    return foldl(proc, init, reversed(sequence0), *(reversed(s) for s in sequences))

def reducel(proc, sequence, init=None):
    """Foldl for a single sequence.

    Like functools.reduce, but uses ``proc(elt, acc)`` like Racket."""
    it = iter(sequence)
    if not init:
        try:
            init = next(it)
        except StopIteration:
            return None  # empty input sequence
    return foldl(proc, init, it)

def reducer(proc, sequence, init=None):
    """Like reducel, but fold from the right (walk the sequence backwards)."""
    return reducel(proc, reversed(sequence), init)

def composer1(*fs):
    """Like composer, but limited to one-argument functions. Faster.

    Example::

        double = lambda x: 2*x
        inc    = lambda x: x+1
        inc_then_double = composer1(double, inc)
        assert inc_then_double(3) == 8
    """
    def compose1_two(f, g):
        return lambda x: f(g(x))
    return reducer(compose1_two, fs)  # op(elt, acc)

def composel1(*fs):
    """Like composel, but limited to one-argument functions. Faster.

    Example::

        double = lambda x: 2*x
        inc    = lambda x: x+1
        double_then_inc = composel(double, inc)
        assert double_then_inc(3) == 7
    """
    return composer1(*reversed(fs))

def composer(*fs):
    """Compose functions accepting only positional args. Right to left.

    This mirrors the standard mathematical convention (f ∘ g)(x) ≡ f(g(x)).

    The output from the previous function is unpacked to the argument list
    of the next one. If the duck test fails, the output is assumed to be
    a single value, and is fed in to the next function as-is.
    """
    def unpack_ctx(*args): pass  # just a context where we can use * to unpack
    def compose_two(f, g):
        def composed(*args):
            a = g(*args)
            try:
                unpack_ctx(*a)
            except TypeError:
                return f(a)
            else:
                return f(*a)
        return composed
    return reducer(compose_two, fs)  # op(elt, acc)

def composel(*fs):
    """Like composer, but from left to right.

    The sequence ``fs`` is applied in the order given; no need
    to read the source code backwards.
    """
    return composer(*reversed(fs))

# Helpers for multi-arg compose chains
def tokth(k, f):
    """Return a function to apply f to args[k], pass the rest through.

    Negative indices also supported.

    Especially useful in multi-arg compose chains. See ``test()`` for examples.
    """
    def applicator(*args):
        n = len(args)
        nonlocal k
        if k < 0:
            k = k % n
        m = k + 1
        if n < m:
            raise TypeError("Expected at least {:d} arguments, got {:d}".format(m, n))
        out = list(args[:k])
        out.append(f(args[k]))  # mth argument
        if n > m:
            out.extend(args[m:])
        return tuple(out)
    return applicator

def to1st(f):
    """Return a function to apply f to first item in args, pass the rest through.

    Example::

        nil = ()
        def cons(x, l):  # elt, acc
            return (x,) + l
        def mymap_one(f, sequence):
            f_then_cons = composer(cons, to1st(f))  # args: elt, acc
            return foldr(f_then_cons, nil, sequence)
        double = lambda x: 2*x
        assert mymap_one(double, (1, 2, 3)) == (2, 4, 6)
    """
    return tokth(0, f)  # this is just a partial() but we want to provide a docstring.

def to2nd(f):
    """Return a function to apply f to second item in args, pass the rest through."""
    return tokth(1, f)

def tolast(f):
    """Return a function to apply f to last item in args, pass the rest through."""
    return tokth(-1, f)

def to(*specs):
    """Return a function to apply f1, ..., fn to items in args, pass the rest through.

    The specs are processed sequentially in the given order (allowing also
    multiple updates to the same item).

    Parameters:
        specs: tuple of `(k, f)`, where:
            k: int
              index (also negative supported)
            f: function
              One-argument function to apply to `args[k]`.

    Returns:
        Function to (functionally) update args with the specs applied.
    """
    return composel(*(tokth(k, f) for k, f in specs))

def test():
    from collections import Counter
    evaluations = Counter()
    @memoize
    def f(x):
        evaluations[x] += 1
        return x**2
    f(3)
    f(3)
    f(4)
    f(3)
    assert all(n == 1 for n in evaluations.values())

    # "memoize lambda": classic evaluate-at-most-once thunk
    thunk = memoize(lambda: print("hi from thunk"))
    thunk()
    thunk()

    evaluations = 0
    @memoize
    def t():
        nonlocal evaluations
        evaluations += 1
    t()
    t()
    assert evaluations == 1

    # exception storage in memoize
    class AllOkJustTesting(Exception):
        pass
    evaluations = 0
    @memoize
    def t():
        nonlocal evaluations
        evaluations += 1
        raise AllOkJustTesting()
    olderr = None
    for _ in range(3):
        try:
            t()
        except AllOkJustTesting as err:
            if olderr is not None and err is not olderr:
                assert False  # exception instance memoized, should be same every time
            olderr = err
        else:
            assert False  # memoize should not block raise
    assert evaluations == 1

    @curry
    def add3(a, b, c):
        return a + b + c
    assert add3(1)(2)(3) == 6
    # actually uses partial application so these work, too
    assert add3(1, 2)(3) == 6
    assert add3(1)(2, 3) == 6
    assert add3(1, 2, 3) == 6

    @curry
    def lispyadd(*args):
        return sum(args)
    assert lispyadd() == 0  # no args is a valid arity here

    @curry
    def foo(a, b, *, c, d):
        return a, b, c, d
    assert foo(5, c=23)(17, d=42) == (5, 17, 23, 42)

    # currying a thunk is essentially a no-op
    evaluations = 0
    @curry
    def t():
        nonlocal evaluations
        evaluations += 1
    t()
    assert evaluations == 1  # t has no args, so it should have been invoked

    # flip
    def f(a, b):
        return (a, b)
    assert f(1, 2) == (1, 2)
    assert (flip(f))(1, 2) == (2, 1)
    assert (flip(f))(1, b=2) == (1, 2)  # b -> kwargs

    nil = ()
    def cons(x, l):  # elt, acc
        return (x,) + l
    assert foldl(cons, nil, (1, 2, 3)) == (3, 2, 1)
    assert foldr(cons, nil, (1, 2, 3)) == (1, 2, 3)

    from operator import add
    assert reducel(add, (1, 2, 3)) == 6
    assert reducer(add, (1, 2, 3)) == 6

    def foo(a, b, acc):
        return acc + ((a, b),)
    assert foldl(foo, (), (1, 2, 3), (4, 5)) == ((1, 4), (2, 5))
    assert foldr(foo, (), (1, 2, 3), (4, 5)) == ((3, 5), (2, 4))

    double = lambda x: 2*x
    inc    = lambda x: x+1
    inc_then_double = composer1(double, inc)
    double_then_inc = composel1(double, inc)
    assert inc_then_double(3) == 8
    assert double_then_inc(3) == 7

    assert to1st(double)(1, 2, 3)  == (2, 2, 3)
    assert to2nd(double)(1, 2, 3)  == (1, 4, 3)
    assert tolast(double)(1, 2, 3) == (1, 2, 6)

    def mymap_one(f, sequence):
        f_then_cons = composer(cons, to1st(f))  # args: elt, acc
        return foldr(f_then_cons, nil, sequence)
    assert mymap_one(double, (1, 2, 3)) == (2, 4, 6)
    def mymap_one2(f, sequence):
        f_then_cons = composel(to1st(f), cons)  # args: elt, acc
        return foldr(f_then_cons, nil, sequence)
    assert mymap_one2(double, (1, 2, 3)) == (2, 4, 6)

    # point-free-ish style
    mymap_one3 = lambda f: partial(foldr, composer(cons, to1st(f)), nil)
    doubler = mymap_one3(double)
    assert doubler((1, 2, 3)) == (2, 4, 6)

    try:
        doubler((1, 2, 3), (4, 5, 6))
    except TypeError:
        pass
    else:
        assert False  # one arg too many; cons in the compose chain expects 2 args

    # minimum arity of fold functions is 3, to allow use with curry:
    mymap_one4 = lambda f: (curry(foldr))(composer(cons, to1st(f)), nil)
    doubler = mymap_one4(double)
    assert doubler((1, 2, 3)) == (2, 4, 6)

    processor = to((0, double),
                   (-1, inc),
                   (1, composer(double, double)),
                   (0, inc))
    assert processor(1, 2, 3) == (3, 8, 4)

    def zipper(*args):
        *rest, acc = args
        return acc + (tuple(rest),)
    myzipl = (curry(foldl))(zipper, ())
    myzipr = (curry(foldr))(zipper, ())
    assert myzipl((1, 2, 3), (4, 5, 6), (7, 8)) == ((1, 4, 7), (2, 5, 8))
    assert myzipr((1, 2, 3), (4, 5, 6), (7, 8)) == ((3, 6, 8), (2, 5, 7))

    print("All tests PASSED")

if __name__ == '__main__':
    test()