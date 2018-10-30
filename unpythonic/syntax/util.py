# -*- coding: utf-8 -*-
"""Utilities for working with syntax."""

from functools import partial

from ast import Call, Name, Attribute, Lambda, FunctionDef
from unpythonic.syntax.astcompat import AsyncFunctionDef

from macropy.core import Captured
from macropy.core.walkers import Walker

def isx(tree, x, allow_attr=True):
    """Check if tree is a reference to an object by the name ``x`` (str).

    ``x`` is recognized both as a bare name and as an attribute, to support
    both from-imports and regular imports of ``somemodule.x``.

    Additionally, we detect ``x`` inside ``Captured`` nodes, which may be
    inserted during macro expansion.

    allow_attr: can be set to ``False`` to disregard ``Attribute`` nodes.
    """
    # WTF, so sometimes there **is** a Captured node, while sometimes there isn't (_islet)? At which point are these removed?
    # Captured nodes only come from unpythonic.syntax, and we use from-imports
    # and bare names for anything hq[]'d; but explicit references may use either
    # bare names or somemodule.f.
    return (type(tree) is Name and tree.id == x) or \
           (type(tree) is Captured and tree.name == x) or \
           (allow_attr and type(tree) is Attribute and tree.attr == x)

def islet(tree):
    """Test whether tree is an already expanded ``let[]``, ``letseq[]`` or ``letrec[]``."""
    # name must match what ``unpythonic.syntax.letdo._letimpl`` uses in its output.
    return type(tree) is Call and isx(tree.func, "letter", allow_attr=False)

def isdo(tree):
    """Detect whether tree is an already expanded ``do[]``."""
    # name must match what ``unpythonic.syntax.letdo.do`` uses in its output.
    return type(tree) is Call and isx(tree.func, "dof")

def isec(tree, known_ecs):
    """Check if tree is a call to a function known to be an escape continuation.

    known_ec: list of str, names of known escape continuations.

    Only bare-name references are supported.
    """
    return type(tree) is Call and type(tree.func) is Name and tree.func.id in known_ecs

@Walker
def detect_callec(tree, *, collect, **kw):
    """Collect names of escape continuations from call_ec invocations in tree.

    Currently supported and unsupported cases::

        # use as decorator, supported
        @call_ec
        def result(ec):  # <-- we grab name "ec" from here
            ...

        # use directly on a literal lambda, supported
        result = call_ec(lambda ec: ...)  # <-- we grab name "ec" from here

        # use as a function, **NOT supported**
        def g(ec):           # <-- should grab from here
            ...
        ...
        result = call_ec(g)  # <-- but this is here; g could be in another module
    """
    # literal function names that are always interpreted as an ec.
    # "brk" is needed to combo with unpythonic.fploop.breakably_looped.
    fallbacks = ["ec", "brk"]
    for x in fallbacks:
        collect(x)
    iscallec = partial(isx, x="call_ec")
    # TODO: add support for general use of call_ec as a function (difficult)
    if type(tree) in (FunctionDef, AsyncFunctionDef) and any(iscallec(deco) for deco in tree.decorator_list):
        fdef = tree
        collect(fdef.args.args[0].arg)  # FunctionDef.arguments.(list of arg objects).arg
    # TODO: decorated lambdas with other decorators in between
    elif type(tree) is Call and iscallec(tree.func) and type(tree.args[0]) is Lambda:
        lam = tree.args[0]
        collect(lam.args.args[0].arg)
    return tree

@Walker
def detect_lambda(tree, *, collect, stop, **kw):
    """Find lambdas in tree. Helper for block macros.

    Run ``_detect_lambda.collect(tree)`` in the first pass, before allowing any
    nested macros to expand. (Those may generate more lambdas that your block
    macro is not interested in).

    The return value from ``.collect`` is a ``list``of ``id(lam)``, where ``lam``
    is a Lambda node that appears in ``tree``. This list is suitable as
    ``userlambdas`` for the TCO macros.

    This ignores any "lambda e: ..." added by an already expanded ``do[]``,
    to allow other block macros to better work together with ``with multilambda``
    (which expands in the first pass, to eliminate semantic surprises).
    """
    if isdo(tree):
        stop()
        for item in tree.args:  # each arg to dof() is a lambda
            detect_lambda.collect(item.body)
    if type(tree) is Lambda:
        collect(id(tree))
    return tree

def is_decorator(tree, fname):
    """Test tree whether it is the decorator ``fname``.

    References of the forms ``f``, ``foo.f`` and ``hq[f]`` are supported.

     We detect:

        - ``Name``, ``Attribute`` or ``Captured`` matching the given ``fname``
          (non-parametric decorator), and

        - ``Call`` whose ``.func`` matches the above rule (parametric decorator).
    """
    return isx(tree, fname) or \
           (type(tree) is Call and isx(tree.func, fname))

def is_lambda_decorator(tree, fname):
    """Test tree whether it decorates a lambda with ``fname``.

    A node is detected as a lambda decorator if it is a ``Call`` that supplies
    exactly one positional argument, and its ``.func`` is the decorator ``fname``
    (``_is_decorator(tree.func, fname)`` returns ``True``).

    This function does not know or care whether a chain of ``Call`` nodes
    terminates in a ``Lambda`` node. See ``_is_decorated_lambda``.

    Examples::

        trampolined(arg)                    # --> non-parametric decorator
        looped_over(range(10), acc=0)(arg)  # --> parametric decorator
    """
    return (type(tree) is Call and len(tree.args) == 1) and is_decorator(tree.func, fname)

# Extensible system. List known decorators in the desired ordering,
# outermost-to-innermost.
#
# "with curry" (--> hq[curryf(...)]) is expanded later, so we don't need to
# worry about it here; we catch only explicit curry(...) in the client code,
# which is already there when "with tco" or "with continuations" is expanded.
#
# We use tuples to emphasize that for now, these are immutable at run-time.
# (The main issue is lambda_decorator_detectors must be kept up to date;
#  requires too much code if there is no real need to modify this at run-time.)
#
tco_decorators = ("trampolined", "looped", "breakably_looped", "looped_over", "breakably_looped_over")
decorator_registry = ("memoize", "fimemoize") + tco_decorators + ("call_ec", "call", "curry")
lambda_decorator_detectors = tuple(partial(is_lambda_decorator, fname=x) for x in decorator_registry)

def is_decorated_lambda(tree, detectors=lambda_decorator_detectors):
    """Detect a tree of the form f(g(h(lambda ...: ...)))

    We currently support known decorators only.

    detectors: a list of predicates to detect a known decorator.
    To build these easily, ``partial(is_lambda_decorator, fname="whatever")``.

    The default list tests against those that were, at startup time, in
    ``unpythonic.syntax.util.decorator_registry``.
    """
    if type(tree) is not Call:
        return False
    if not any(f(tree) for f in detectors):
        return False
    if type(tree.args[0]) is Lambda:
        return True
    return is_decorated_lambda(tree.args[0], detectors)

def destructure_decorated_lambda(tree):
    """Get the AST nodes for ([f, g, h], lambda) in f(g(h(lambda ...: ...)))

    Input must be a tree for which ``is_decorated_lambda`` returns ``True``.

    This returns **the original AST nodes**, to allow in-place transformations.
    """
    def get(tree, lst):
        if type(tree) is Call:
            # collect tree itself, not tree.func, because we need to reorder the funcs later.
            return get(tree.args[0], lst + [tree])
        elif type(tree) is Lambda:
            return lst, tree
        assert False, "Expected a chain of Call nodes terminating in a Lambda node"
    return get(tree, [])

def has_tco(tree, userlambdas=[]):
    """Return whether a FunctionDef or a decorated lambda has TCO applied.

    userlambdas: list; when detecting a lambda, only consider it if its id
    matches one of those in the list.

    Return value is ``True`` or ``False`` (depending on test result) if the
    test was applicable, and ``None`` if it was not applicable.
    """
    if type(tree) in (FunctionDef, AsyncFunctionDef):
        return any(is_decorator(x, fname) for fname in tco_decorators for x in tree.decorator_list)
    elif is_decorated_lambda(tree):
        decorator_list, thelambda = destructure_decorated_lambda(tree)
        if (not userlambdas) or (id(thelambda) in userlambdas):
            return any(is_lambda_decorator(x, fname) for fname in tco_decorators for x in decorator_list)
    return None  # not applicable

def fix_lambda_decorators(tree):
    """Fix ordering of known lambda decorators (recursively) in ``tree``.

    Strictly, lambdas have no decorator_list, but can be decorated by explicitly
    surrounding them with calls to decorator functions.

    Examples::
        call_ec(trampolined(lambda ...: ...))
            --> trampolined(call_ec(lambda ...: ...))

        call_ec(curry(trampolined(lambda ...: ...)))
            --> trampolined(call_ec(curry(lambda ...: ...)))
    """
    def prioritize(tree):  # sort key for Call nodes invoking known decorators
        for k, f in enumerate(lambda_decorator_detectors):
            if f(tree):
                return k
        assert False  # we currently support known decorators only

    @Walker
    def fixit(tree, *, stop, **kw):
        if is_decorated_lambda(tree, lambda_decorator_detectors):
            decorator_list, thelambda = destructure_decorated_lambda(tree)
            # We can just swap the func attributes of the nodes.
            ordered_decorator_list = sorted(decorator_list, key=prioritize)
            ordered_funcs = [x.func for x in ordered_decorator_list]
            for thecall, newfunc in zip(decorator_list, ordered_funcs):
                thecall.func = newfunc
            # don't recurse on the tail of the decorator list, but recurse into the lambda body.
            stop()
            fixit.recurse(thelambda.body)
        return tree
    return fixit.recurse(tree)