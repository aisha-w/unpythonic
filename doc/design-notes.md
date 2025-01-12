# Design Notes

- [On ``let`` and Python](#on-let-and-python)
- [Python is Not a Lisp](#python-is-not-a-lisp)
- [Assignment Syntax](#assignment-syntax)
- [TCO Syntax and Speed](#tco-syntax-and-speed)
- [Comboability of Syntactic Macros](#comboability-of-syntactic-macros)
- [No Monads?](#no-monads)
- [Further Explanation](#further-explanation)
- [Notes on Macros](#notes-on-macros)

### On ``let`` and Python

Why no `let*`, as a function? In Python, name lookup always occurs at runtime. Python gives us no compile-time guarantees that no binding refers to a later one - in [Racket](http://racket-lang.org/), this guarantee is the main difference between `let*` and `letrec`.

Even Racket's `letrec` processes the bindings sequentially, left-to-right, but *the scoping of the names is mutually recursive*. Hence a binding may contain a lambda that, when eventually called, uses a binding defined further down in the `letrec` form.

In contrast, in a `let*` form, attempting such a definition is *a compile-time error*, because at any point in the sequence of bindings, only names found earlier in the sequence have been bound. See [TRG on `let`](https://docs.racket-lang.org/guide/let.html).

Our `letrec` behaves like `let*` in that if `valexpr` is not a function, it may only refer to bindings above it. But this is only enforced at run time, and we allow mutually recursive function definitions, hence `letrec`.

Note the function versions of our `let` constructs, presented here, are **not** properly lexically scoped; in case of nested ``let`` expressions, one must be explicit about which environment the names come from.

The [macro versions](../macro_extras/) of the `let` constructs **are** lexically scoped. The macros also provide a ``letseq[]`` that, similarly to Racket's ``let*``, gives a compile-time guarantee that no binding refers to a later one.

Inspiration: [[1]](https://nvbn.github.io/2014/09/25/let-statement-in-python/) [[2]](https://stackoverflow.com/questions/12219465/is-there-a-python-equivalent-of-the-haskell-let) [[3]](http://sigusr2.net/more-about-let-in-python.html).

### Python is not a Lisp

The point behind providing `let` and `begin` (and the ``let[]`` and ``do[]`` [macros](macro_extras/)) is to make Python lambdas slightly more useful - which was really the starting point for this whole experiment.

The oft-quoted single-expression limitation of the Python ``lambda`` is ultimately a herring, as this library demonstrates. The real problem is the statement/expression dichotomy. In Python, the looping constructs (`for`, `while`), the full power of `if`, and `return` are statements, so they cannot be used in lambdas. We can work around some of this:

 - The expression form of `if` can be used, but readability suffers if nested. Actually, [`and` and `or` are sufficient for full generality](https://www.ibm.com/developerworks/library/l-prog/), but readability suffers there too. Another possibility is to use MacroPy to define a ``cond`` expression, but it's essentially duplicating a feature the language already almost has. (Our [macros](macro_extras/) do exactly that, providing a ``cond`` expression as a macro.)
 - Functional looping (with TCO, to boot) is possible.
 - ``unpythonic.ec.call_ec`` gives us ``return`` (the ec), and ``unpythonic.misc.raisef`` gives us ``raise``.
 - Exception handling (``try``/``except``/``else``/``finally``) and context management (``with``) are currently **not** available for lambdas, even in ``unpythonic``.

Still, ultimately one must keep in mind that Python is not a Lisp. Not all of Python's standard library is expression-friendly; some standard functions and methods lack return values - even though a call is an expression! For example, `set.add(x)` returns `None`, whereas in an expression context, returning `x` would be much more useful, even though it does have a side effect.

### Assignment syntax

Why the clunky `e.set("foo", newval)` or `e << ("foo", newval)`, which do not directly mention `e.foo`? This is mainly because in Python, the language itself is not customizable. If we could define a new operator `e.foo <op> newval` to transform to `e.set("foo", newval)`, this would be easily solved.

Our [macros](macro_extras/) essentially do exactly this, but by borrowing the ``<<`` operator to provide the syntax ``foo << newval``, because even with MacroPy, it is not possible to define new [BinOp](https://greentreesnakes.readthedocs.io/en/latest/nodes.html#BinOp)s in Python. That would be possible essentially as a *reader macro* (as it's known in the Lisp world), to transform custom BinOps into some syntactically valid Python code before proceeding with the rest of the import machinery, but it seems as of this writing, no one has done this.

Without macros, in raw Python, we could abuse `e.foo << newval`, which transforms to `e.foo.__lshift__(newval)`, to essentially perform `e.set("foo", newval)`, but this requires some magic, because we then need to monkey-patch each incoming value (including the first one when the name "foo" is defined) to set up the redirect and keep it working.

 - Methods of builtin types such as `int` are read-only, so we can't just override `__lshift__` in any given `newval`.
 - For many types of objects, at the price of some copy-constructing, we can provide a wrapper object that inherits from the original's type, and just adds an `__lshift__` method to catch and redirect the appropriate call. See commented-out proof-of-concept in [`unpythonic/env.py`](unpythonic/env.py).
 - But that approach doesn't work for function values, because `function` is not an acceptable base type to inherit from. In this case we could set up a proxy object, whose `__call__` method calls the original function (but what about the docstring and such? Is `@functools.wraps` enough?). But then there are two kinds of wrappers, and the re-wrapping logic (which is needed to avoid stacking wrappers when someone does `e.a << e.b`) needs to know about that.
 - It's still difficult to be sure these two approaches cover all cases; a read of `e.foo` gets a wrapped value, not the original; and this already violates [The Zen of Python](https://www.python.org/dev/peps/pep-0020/) #1, #2 and #3.

If we later choose go this route nevertheless, `<<` is a better choice for the syntax than `<<=`, because `let` needs `e.set(...)` to be valid in an expression context.

The current solution for the assignment syntax issue is to use macros, to have both clean syntax at the use site and a relatively hackfree implementation.

### TCO syntax and speed

Benefits and costs of ``return jump(...)``:

 - Explicitly a tail call due to ``return``.
 - The trampoline can be very simple and (relatively speaking) fast. Just a dumb ``jump`` record, a ``while`` loop, and regular function calls and returns.
 - The cost is that ``jump`` cannot detect whether the user forgot the ``return``, leaving a possibility for bugs in the client code (causing an FP loop to immediately exit, returning ``None``). Unit tests of client code become very important.
   - This is somewhat mitigated by the check in `__del__`, but it can only print a warning, not stop the incorrect program from proceeding.
   - We could mandate that trampolined functions must not return ``None``, but:
     - Uniformity is lost between regular and trampolined functions, if only one kind may return ``None``.
     - This breaks the *don't care about return value* use case, which is rather common when using side effects.
     - Failing to terminate at the intended point may well fall through into what was intended as another branch of the client code, which may correctly have a ``return``. So this would not even solve the problem.

The other simple-ish solution is to use exceptions, making the jump wrest control from the caller. Then ``jump(...)`` becomes a verb, but this approach is 2-5x slower, when measured with a do-nothing loop. (See the old default TCO implementation in v0.9.2.)

Our [macros](macro_extras/) provide an easy-to use solution. Just wrap the relevant section of code in a ``with tco:``, to automatically apply TCO to code that looks exactly like standard Python. With the macro, function definitions (also lambdas) and returns are automatically converted. It also knows enough not to add a ``@trampolined`` if you have already declared a ``def`` as ``@looped`` (or any of the other TCO-enabling decorators in ``unpythonic.fploop``).

For other libraries bringing TCO to Python, see:

 - [tco](https://github.com/baruchel/tco) by Thomas Baruchel, based on exceptions.
 - [ActiveState recipe 474088](https://github.com/ActiveState/code/tree/master/recipes/Python/474088_Tail_Call_Optimization_Decorator), based on ``inspect``.
 - ``recur.tco`` in [fn.py](https://github.com/fnpy/fn.py), the original source of the approach used here.
 - [MacroPy](https://github.com/azazel75/macropy) uses an approach similar to ``fn.py``.

### Comboability of Syntactic Macros

Making macros work together is nontrivial, essentially because *macros don't compose*. [As pointed out by John Shutt](https://fexpr.blogspot.com/2013/12/abstractive-power.html), in a multilayered language extension implemented with macros, the second layer of macros needs to understand all of the first layer. The issue is that the macro abstraction leaks the details of its expansion. Contrast with functions, which operate on values: the process that was used to arrive at a value doesn't matter. It's always possible for a function to take this value and transform it into another value, which can then be used as input for the next layer of functions. That's composability at its finest.

The need for interaction between macros may arise already in what *feels* like a single layer of abstraction; for example, it's not only that the block macros must understand ``let[]``, but some of them must understand other block macros. This is because what feels like one layer of abstraction is actually implemented as a number of separate macros, which run in a specific order. Thus, from the viewpoint of actually applying the macros, if the resulting software is to work correctly, the mere act of allowing combos between the block macros already makes them into a multilayer system. The compartmentalization of conceptually separate features into separate macros facilitates understanding and maintainability, but fails to reach the ideal of modularity.

Therefore, any particular combination of macros that has not been specifically tested might not work. That said, if some particular combo doesn't work and *is not at least documented as such*, that's an error; please raise an issue. The unit tests should cover the combos that on the surface seem the most useful, but there's no guarantee that they cover everything that actually is useful somewhere.

### No Monads

(Beside List inside ``forall``.)

Admittedly unpythonic, but Haskell feature, not Lisp. Besides, already done elsewhere, see [OSlash](https://github.com/dbrattli/OSlash) if you need them.

If you want to roll your own monads for whatever reason, there's [this silly hack](https://github.com/Technologicat/python-3-scicomp-intro/blob/master/examples/monads.py) that wasn't packaged into this; or just read Stephan Boyer's quick introduction [[part 1]](https://www.stephanboyer.com/post/9/monads-part-1-a-design-pattern) [[part 2]](https://www.stephanboyer.com/post/10/monads-part-2-impure-computations) [[super quick intro]](https://www.stephanboyer.com/post/83/super-quick-intro-to-monads) and figure it out, it's easy. (Until you get to `State` and `Reader`, where [this](http://brandon.si/code/the-state-monad-a-tutorial-for-the-confused/) and maybe [this](https://gaiustech.wordpress.com/2010/09/06/on-monads/) can be helpful.)

### Further Explanation

Your hovercraft is full of eels!

[Naturally](http://stupidpythonideas.blogspot.com/2015/05/spam-spam-spam-gouda-spam-and-tulips.html), they come with the territory.

Some have expressed the opinion [the statement-vs-expression dichotomy is a feature](http://stupidpythonideas.blogspot.com/2015/01/statements-and-expressions.html). The BDFL himself has famously stated that TCO has no place in Python [[1]](http://neopythonic.blogspot.com/2009/04/tail-recursion-elimination.html) [[2]](http://neopythonic.blogspot.fi/2009/04/final-words-on-tail-calls.html), and less famously that multi-expression lambdas or continuations have no place in Python [[3]](https://www.artima.com/weblogs/viewpost.jsp?thread=147358). Several potentially interesting PEPs have been deferred [[1]](https://www.python.org/dev/peps/pep-3150/) [[2]](https://www.python.org/dev/peps/pep-0403/) or rejected [[3]](https://www.python.org/dev/peps/pep-0511/) [[4]](https://www.python.org/dev/peps/pep-0463/) [[5]](https://www.python.org/dev/peps/pep-0472/).

Of course, if I agreed, I wouldn't be doing this (or [this](https://github.com/Technologicat/pydialect)).

On a point raised [here](https://www.artima.com/weblogs/viewpost.jsp?thread=147358) with respect to indentation-sensitive vs. indentation-insensitive parser modes, having seen [sweet expressions](https://srfi.schemers.org/srfi-110/srfi-110.html) I think Python is confusing matters by linking the mode to statements vs. expressions. A workable solution is to make *everything* support both modes (or even preprocess the source code text to use only one of the modes), which *uniformly* makes parentheses an alternative syntax for grouping.

It would be nice to be able to use indentation to structure expressions to improve their readability, like one can do in Racket with [sweet](https://docs.racket-lang.org/sweet/), but I suppose ``lambda x: [expr0, expr1, ...]`` will have to do for a multiple-expression lambda in MacroPy. Unless I decide at some point to make a source filter for [Pydialect](https://github.com/Technologicat/pydialect) to auto-convert between indentation and parentheses; but for Python this is somewhat difficult to do, because statements **must** use indentation whereas expressions **must** use parentheses, and this must be done before we can invoke the standard parser to produce an AST.

### Notes on Macros

 - ``continuations`` and ``tco`` are mutually exclusive, since ``continuations`` already implies TCO.
   - However, the ``tco`` macro skips any ``with continuations`` blocks inside it, **for the specific reason** of allowing modules written in the [Lispython dialect](https://github.com/Technologicat/pydialect) (which implies TCO for the whole module) to use ``with continuations``.

 - ``prefix``, ``autoreturn``, ``quicklambda`` and ``multilambda`` are first-pass macros (expand from outside in), because they change the semantics:
   - ``prefix`` transforms things-that-look-like-tuples into function calls,
   - ``autoreturn`` adds ``return`` statements where there weren't any,
   - ``quicklambda`` transforms things-that-look-like-list-lookups into ``lambda`` function definitions,
   - ``multilambda`` transforms things-that-look-like-lists (in the body of a ``lambda``) into sequences of multiple expressions, using ``do[]``.
   - Hence, a lexically outer block of one of these types *will expand first*, before any macros inside it are expanded, in contrast to the default *from inside out* expansion order.
   - This yields clean, standard-ish Python for the rest of the macros, which then don't need to worry about their input meaning something completely different from what it looks like.

 - An already expanded ``do[]`` (including that inserted by `multilambda`) is accounted for by all ``unpythonic.syntax`` macros when handling expressions.
   - For simplicity, this is **the only** type of sequencing understood by the macros.
   - E.g. the more rudimentary ``unpythonic.seq.begin`` is not treated as a sequencing operation. This matters especially in ``tco``, where it is critically important to correctly detect a tail position in a return-value expression or (multi-)lambda body.
   - *Sequencing* is here meant in the Racket/Haskell sense of *running sub-operations in a specified order*, unrelated to Python's *sequences*.

 - The TCO transformation knows about TCO-enabling decorators provided by ``unpythonic``, and adds the ``@trampolined`` decorator to a function definition only when it is not already TCO'd.
   - This applies also to lambdas; they are decorated by directly wrapping them with a call: ``trampolined(lambda ...: ...)``.
   - This allows ``with tco`` to work together with the functions in ``unpythonic.fploop``, which imply TCO.

 - Macros that transform lambdas (notably ``continuations`` and ``tco``):
   - Perform a first pass to take note of all lambdas that appear in the code *before the expansion of any inner macros*. Then in the second pass, *after the expansion of all inner macros*, only the recorded lambdas are transformed.
     - This mechanism distinguishes between explicit lambdas in the client code, and internal implicit lambdas automatically inserted by a macro. The latter are a technical detail that should not undergo the same transformations as user-written explicit lambdas.
     - The identification is based on the ``id`` of the AST node instance. Hence, if you plan to write your own macros that work together with those in ``unpythonic.syntax``, avoid going overboard with FP. Modifying the tree in-place, preserving the original AST node instances as far as sensible, is just fine.
     - For the interested reader, grep the source code for ``userlambdas``.
   - Support a limited form of *decorated lambdas*, i.e. trees of the form ``f(g(h(lambda ...: ...)))``.
     - The macros will reorder a chain of lambda decorators (i.e. nested calls) to use the correct ordering, when only known decorators are used on a literal lambda.
       - This allows some combos such as ``tco``, ``unpythonic.fploop.looped``, ``curry``.
     - Only decorators provided by ``unpythonic`` are recognized, and only some of them are supported. For details, see ``unpythonic.regutil``.
     - If you need to combo ``unpythonic.fploop.looped`` and ``unpythonic.ec.call_ec``, use ``unpythonic.fploop.breakably_looped``, which does exactly that.
       - The problem with a direct combo is that the required ordering is the trampoline (inside ``looped``) outermost, then ``call_ec``, and then the actual loop, but because an escape continuation is only valid for the dynamic extent of the ``call_ec``, the whole loop must be run inside the dynamic extent of the ``call_ec``.
       - ``unpythonic.fploop.breakably_looped`` internally inserts the ``call_ec`` at the right step, and gives you the ec as ``brk``.
     - For the interested reader, look at ``unpythonic.syntax.util``.

 - ``namedlambda`` is a two-pass macro. In the first pass (outside-in), it names lambdas inside ``let[]`` expressions before they are expanded away. The second pass (inside-out) of ``namedlambda`` must run after ``curry`` to analyze and transform the auto-curried code produced by ``with curry``. In most cases, placing ``namedlambda`` in a separate outer ``with`` block runs both operations in the correct order.

 - ``autoref`` does not need in its output to be curried (hence after ``curry`` to gain some performance), but needs to run before ``lazify``, so that both branches of each transformed reference get the implicit forcing. Its transformation is orthogonal to what ``namedlambda`` does, so it does not matter in which exact order these two run.

 - ``lazify`` is a rather invasive rewrite that needs to see the output from most of the other macros.

 - ``envify`` needs to see the output of ``lazify`` in order to shunt function args into an unpythonic ``env`` without triggering the implicit forcing.

 - Some of the block macros can be comboed as multiple context managers in the same ``with`` statement (expansion order is then *left-to-right*), whereas some (notably ``curry`` and ``namedlambda``) require their own ``with`` statement.
   - This is a [known issue in MacroPy](https://github.com/azazel75/macropy/issues/21). I have made a [fix](https://github.com/azazel75/macropy/pull/22), but still need to make proper test cases to get it merged.
   - If something goes wrong in the expansion of one block macro in a ``with`` statement that specifies several block macros, surprises may occur.
   - When in doubt, use a separate ``with`` statement for each block macro that applies to the same section of code, and nest the blocks.
     - Test one step at a time with the ``macropy.tracing.show_expanded`` block macro to make sure the expansion looks like what you intended.
