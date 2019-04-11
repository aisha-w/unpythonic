# -*- coding: utf-8 -*-
"""Ultralight math notebook.

Auto-print top-level expressions, auto-assign last result as _.

Also provided is a debug printer, which prints both the expression source code
and its value.
"""

# This is the kind of thing thinking with macros does to your program. ;)

from ast import Expr, Call, Name, Tuple, keyword

from macropy.core.quotes import macros, q, u, ast_literal
from macropy.core.hquotes import macros, hq
from macropy.core.walkers import Walker
from macropy.core import unparse

from ..dynassign import dyn

def nb(body, args):
    p = args[0] if args else q[print]  # custom print function hook
    newbody = []
    with q as init:
        _ = None
        theprint = ast_literal[p]
    newbody.extend(init)
    for stmt in body:
        if type(stmt) is not Expr:
            newbody.append(stmt)
            continue
        with q as newstmts:
            _ = ast_literal[stmt.value]
            if _ is not None:
                theprint(_)
        newbody.extend(newstmts)
    return newbody

# -----------------------------------------------------------------------------

# TODO: refactor dbg into its own module

def dbgprint_block(ks, vs, *, filename=None, lineno=None, sep=", ", **kwargs):
    """Default debug printer for the ``dbg`` macro, block variant.

    The default print format looks like::

        [/home/developer/codes/foo.py:42] x: 2, y: 3, (17 + 23): 40

    Parameters:

        ``ks``: ``tuple``
            expressions as strings

        ``vs``: ``tuple``
            the corresponding values

        ``filename``: ``str``
            filename where the debug print call occurred

        ``lineno``: number or ``None``
            line number where the debug print call occurred

        ``sep``: ``str``
            separator as in built-in ``print``,
            used between the expression/value pairs.

        ``kwargs``: anything
            passed through to built-in ``print``

    **Implementing a custom debug printer**:

    When implementing a custom print function, it **must** accept two
    positional arguments, ``ks`` and ``vs``, and two by-name arguments,
    ``filename`` and ``lineno``.

    It may also accept other arguments (see built-in ``print``), or just
    ``**kwargs`` them through to the built-in ``print``, if you like.

    Other arguments are only needed if the print calls in the ``dbg`` sections
    of your client code use them. (To be flexible, this default debug printer
    supports ``sep`` and passes everything else through.)

    The ``lineno`` argument may be ``None`` if the input resulted from macro
    expansion and the macro that generated it didn't bother to fill in the
    ``lineno`` attribute of the AST node.
    """
    header = "[{}:{}] ".format(filename, lineno)
    if "\n" in sep:
        print(sep.join("{} {}: {}".format(header, k, v) for k, v in zip(ks, vs)), **kwargs)
    else:
        print(header + sep.join("{}: {}".format(k, v) for k, v in zip(ks, vs)), **kwargs)

def dbg_block(body, args):
    if args:  # custom print function hook
        # TODO: add support for Attribute to support using a method as a custom print function
        # (the problem is we must syntactically find matches in the AST, and AST nodes don't support comparison)
        if type(args[0]) is not Name:
            assert False, "Custom debug print function must be specified by a bare name"
        p = args[0]
        pname = p.id  # name of the print function as it appears in the user code
    else:
        p = hq[dbgprint_block]
        pname = "print"

    @Walker
    def transform(tree, **kw):
        if type(tree) is Call and type(tree.func) is Name and tree.func.id == pname:
            names = [q[u[unparse(node)]] for node in tree.args]  # x --> "x"; (1 + 2) --> "(1 + 2)"; ...
            names = Tuple(elts=names, lineno=tree.lineno, col_offset=tree.col_offset)
            values = Tuple(elts=tree.args, lineno=tree.lineno, col_offset=tree.col_offset)
            tree.args = [names, values]
            # can't use inspect.stack in the printer itself because we want the line number *before macro expansion*.
            tree.keywords += [keyword(arg="filename", value=q[__file__]),
                              keyword(arg="lineno", value=(q[u[tree.lineno]] if hasattr(tree, "lineno") else q[None]))]
            tree.func = q[ast_literal[p]]
        return tree

    return [transform.recurse(stmt) for stmt in body]

def dbgprint_expr(k, v, *, filename, lineno):
    """Default debug printer for the ``dbg`` macro, expression variant.

    The default print format looks like::

        [/home/developer/codes/foo.py:42] (17 + 23): 40

    Parameters:

        ``k``: ``str``
            the expression source code

        ``v``: anything
            the corresponding value

        ``filename``: ``str``
            filename of the expression being debug-printed

        ``lineno``: number or ``None``
            line number of the expression being debug-printed

    **Implementing a custom debug printer**:

    When implementing a custom print function, it **must** accept two
    positional arguments, ``k`` and ``v``, and two by-name arguments,
    ``filename`` and ``lineno``.

    It **must** return ``v``, because the ``dbg[]`` macro replaces the
    original expression with the print call.

    The ``lineno`` argument may be ``None`` if the input expression resulted
    from macro expansion and the macro that generated it didn't bother to
    fill in the ``lineno`` attribute of the AST node.
    """
    print("[{}:{}] {}: {}".format(filename, lineno, k, v))
    return v  # IMPORTANT!

def dbg_expr(tree):
    ln = q[u[tree.lineno]] if hasattr(tree, "lineno") else q[None]
    return q[dbgprint_expr(u[unparse(tree)], ast_literal[tree], filename=__file__, lineno=ast_literal[ln])]

# -----------------------------------------------------------------------------

# TODO: refactor pop_while into its own module

# Imperative list handling tool::
#
#     with pop_while(name, expr):
#         ...
#
#     with pop_while(expr):
#         ...
#
# transforms into::
#
#     name = expr   # or (gensym) = expr in the 1-arg form
#     while name:
#         it = name.pop(0)  # "it" is literal, visible in user code
#         ...
#
# The point is the user code may append to or extend the list ``name``;
# this simplifies writing some algorithms.
#
def pop_while(body, args):
    gen_sym = dyn.gen_sym
    if len(args) == 1:
        theinput = args[0]
        thename = gen_sym("_tmp")
    elif len(args) == 2:
        theinput = args[1]
        thename = args[0]
        if type(thename) is not Name:
            assert False, "in the two-argument form, the first argument must be a bare name"
        thename = thename.id
    else:
        assert False, "pop_while takes exactly one or two arguments"

    with q as newbody:
        __the_tmp = ast_literal[theinput]
        while __the_tmp:
            it = __the_tmp.pop(0)
    thewhile = newbody[-1]
    thewhile.body.extend(body)

    @Walker
    def renametmp(tree, **kw):
        if type(tree) is Name and tree.id == "__the_tmp":
            tree.id = thename
        return tree
    return renametmp.recurse(newbody)
