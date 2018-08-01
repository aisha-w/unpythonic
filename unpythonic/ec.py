#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escape continuations."""

__all__ = ["escape", "setescape", "call_ec"]

from functools import wraps

class escape(Exception):
    """Exception that essentially represents an escape continuation.

    Use ``raise escape(value)`` to escape to the nearest (dynamically) surrounding
    ``@setescape``. The @setescape'd function immediately terminates, returning
    ``value``.

    Trampolined functions may also use ``return escape(value)``; the trampoline
    will then raise the exception (this is to make it work also with lambdas).

    Constructor parameters:

        value: anything
            The value to send to the escape point.

        tag: anything comparable with ``==``
            Can be used to restrict which ``@setescape`` points may catch
            this escape instance.

        allow_catchall: bool
            Whether untagged "catch-all" ``@setescape`` points may catch
            this escape instance (regardless of whether or not we have a tag!).
    """
    def __init__(self, value, tag=None, allow_catchall=True):
        self.value = value
        self.tag = tag
        self.allow_catchall = allow_catchall

def setescape(tags=None, catch_untagged=True):
    """Decorator. Mark function as exitable by ``raise escape(value)``.

    In Lisp terms, this essentially captures the escape continuation (ec)
    of the decorated function. The ec can then be invoked by raising escape(value).

    To make this work with lambdas, in trampolined functions it is also legal
    to ``return escape(value)``. The trampoline specifically detects ``escape``
    instances, and performs the ``raise``.

    Technically, this is a decorator factory, since we take parameters.

    Parameters:
        tags: ``t``, or tuple of ``t``
          where ``t`` is anything comparable with ``==``
            A tuple is OR'd, like in ``isinstance()``.

            Restrict which escapes will be caught by this ``@setescape`` point.
            If set, ignore any escapes **that have a tag**, which does not match
            any of the given tags.

        catch_untagged: bool
            Choose whether this ``@setescape`` point catches untagged escapes.

    The exact catch condition is::

        # e is an escape instance
        if (tags is None and e.allow_catchall) or
           (e.tag is None and catch_untagged) or
           (tags is not None and e.tag is not None and e.tag in tags):
            # caught

    The same in English:

    - If we are an untagged "catch-all" point, catch any ``e`` that allows
      catchall. Don't care about whether or not it has a tag.

    - If ``e`` is untagged, catch if we should catch untagged escapes.

    - Both us and ``e`` have tags. Catch if the tag of ``e`` matches one of ours.

    Multi-return using escape continuation::

        @setescape()
        def f():
            def g():
                raise escape("hello from g")  # the arg becomes the return value of f()
                print("not reached")
                return False
            g()
            print("not reached either")
            return False
        assert f() == "hello from g"

    Escape from FP loop::

        @setescape()  # no tag, catch any escape instance
        def f():
            @looped
            def s(loop, acc=0, i=0):
                if i > 5:
                    return escape(acc)  # the argument becomes the return value of f()
                return loop(acc + i, i + 1)
            print("never reached")
            return False
        assert f() == 15

    For more control, tagged escape::

        @setescape("foo")
        def foo():
            @immediate
            @setescape("bar")
            def bar():
                @looped
                def s(loop, acc=0, i=0):
                    if i > 5:
                        return escape(acc, tag="foo")
                    return loop(acc + i, i + 1)
                print("never reached")
                return False
            print("never reached either")
            return False
        assert f() == 15
    """
    if tags is not None:
        if isinstance(tags, (tuple, list)):  # multiple tags
            tags = set(tags)
        else: # single tag
            tags = set((tags,))

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except escape as e:
                if (tags is None and e.allow_catchall) or \
                   (e.tag is None and catch_untagged) or \
                   (tags is not None and e.tag is not None and e.tag in tags):
                    return e.value
                else:  # meant for someone else, pass it on
                    raise
        return decorated
    return decorator

def call_ec(f):
    """Decorator. Call with escape continuation (call/ec).

    Parameters:
        `f`: function
            The function to call. It must take one positional argument,
            the first-class escape continuation (ec).

            The ec, in turn, takes one positional argument; the value
            to send to the escape point. It becomes the return value
            of the ``call_ec``.

            The ec instance and the escape point are connected one-to-one.
            Both are tagged with a process-wide unique id. The ec is set to
            disallow catch-all (so that it will always reach its intended
            destination), and the point is set to ignore any untagged escapes
            (so that it catches only this particular ec).

    Like in ``@immediate``, the function ``f`` is called immediately,
    and the def'd name is replaced by the return value of ``f(ec).``

    Example::

        @call_ec
        def result(ec):
            answer = 42
            def inner():
                ec(answer)  # directly escapes from the outer def
                print("never reached")
                return 23
            answer = inner()
            print("never reached either")
            return answer
        assert result == 42

    This can also be used directly, to provide a "return" for multi-expression
    lambdas::

        from unpythonic.misc import begin
        result = call_ec(lambda ec:
                           begin(print("hi from lambda"),
                                 ec(42),
                                 print("never reached")))
        assert result == 42

    Similar usage is valid for named functions, too.
    """
    # We need a process-wide unique id to tag the ec:
    anchor = object()
    uid = id(anchor)
    # Closure property important here. "ec" itself lives as long as someone
    # retains a reference to it. It's a first-class value; the callee could
    # return it or stash it somewhere.
    #
    # So we must keep track of whether we're still inside the dynamic extent
    # of the call/ec - i.e. whether we can still catch the escape exception
    # if it is raised.
    ec_valid = True
    # First-class ec like in Lisps. What's first-class in Python? Functions!
    def ec(value):
        if not ec_valid:
            raise RuntimeError("Cannot escape after the dynamic extent of the call_ec invocation.")
        # Be catchable only by our own escape point.
        raise escape(value, uid, allow_catchall=False)
    try:
        # Set up a tagged escape point here and call f.
        # Catch only the one specific ec we just set up.
        @setescape(uid, catch_untagged=False)
        def wrapper():
            return f(ec)
        return wrapper()
    finally:  # Our dynamic extent ends; this ec instance is no longer valid.
              # Clear the flag (it will live on in the closure of the ec instance).
        ec_valid = False

def test():
    # "multi-return" using escape continuation
    @setescape()
    def f():
        def g():
            raise escape("hello from g")  # the argument becomes the return value of f()
            print("not reached")
        g()
        print("not reached either")
    assert f() == "hello from g"

    # lispy call/ec (call-with-escape-continuation)
    @call_ec
    def result(ec):  # effectively, just a code block!
        answer = 42
        ec(answer)  # here this has the same effect as "return answer"...
        print("never reached")
        answer = 23
        return answer
    assert result == 42

    @call_ec
    def result(ec):
        answer = 42
        def inner():
            ec(answer)  # ...but here this directly escapes from the outer def
            print("never reached")
            return 23
        answer = inner()
        print("never reached either")
        return answer
    assert result == 42

    try:
        @call_ec
        def erroneous(ec):
            return ec
        erroneous(42)  # invalid, dynamic extent of the call_ec has ended
    except RuntimeError:
        pass
    else:
        assert False

    # begin() returns the last value. What if we don't want that?
    from unpythonic.misc import begin
    result = call_ec(lambda ec:
                       begin(print("hi from lambda"),
                             ec(42),  # now we can effectively "return ..." at any point from a lambda!
                             print("never reached")))
    assert result == 42

    # tests with @looped in tco.py to prevent cyclic dependency

    print("All tests PASSED")

if __name__ == '__main__':
    test()