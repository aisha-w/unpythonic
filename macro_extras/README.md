# Language extensions using ``unpythonic.syntax``

Our Python language extensions, as syntactic macros, are built on [MacroPy](https://github.com/azazel75/macropy), from the PyPI package ``macropy3``. If you want to take language extension a step further, see our sister project [Pydialect](https://github.com/Technologicat/pydialect).

The [unit tests that contain usage examples](../unpythonic/syntax/test/) cannot be run directly because macro expansion occurs at import time. Instead, run them via the included [generic MacroPy3 bootstrapper](macropy3). For convenience, ``setup.py`` installs this bootstrapper.\

Please note that there are features that appear in both the pure-Python layer and the macro layer, as well as features that only exist in the macro layer.

**This is semantics, not syntax!**

[Strictly speaking](https://stackoverflow.com/questions/17930267/what-is-the-difference-between-syntax-and-semantics-of-programming-languages), ``True``. We just repurpose Python's existing syntax to give it new meanings. However, in the Racket reference, **a** *syntax* designates a macro, in contrast to a *procedure* (regular function). We provide syntaxes in this particular sense. The name ``unpythonic.syntax`` is also shorter to type than ``unpythonic.semantics``, less obscure, and close enough to convey the intended meaning.

If you want custom *syntax* proper, then you may be interested in [Pydialect](https://github.com/Technologicat/pydialect).

### Set Up

To use the bootstrapper, run:

 `./macropy3 -m some.module` (like `python3 -m some.module`); see `-h` for options.

The tests use relative imports. Invoke them from the top-level directory of ``unpythonic`` as e.g.:

 ``macro_extras/macropy3 -m unpythonic.syntax.test.test_curry``

 This is to make the tests run against the source tree without installing it first. Once you have installed ``unpythonic``, feel free to use absolute imports in your own code, like those shown in this README.

There is no abbreviation for ``memoize(lambda: ...)``, because ``MacroPy`` itself already provides ``lazy`` and ``interned``.

**Currently (12/2018) this requires the latest MacroPy from git HEAD.**

The `macropy3` bootstrapper takes the `-m` option, like `python3 -m mod`. The alternative is to specify a filename positionally, like ``python3 mod.py``. In either case, the bootstrapper will import the module in a special mode that pretends its `__name__ == '__main__'`, to allow using the pythonic conditional main idiom also in macro-enabled code.

*This document doubles as the API reference, but despite maintenance on a best-effort basis, may occasionally be out of date at places. In case of conflicts in documentation, believe the unit tests first; specifically the code, not necessarily the comments. Everything else (comments, docstrings and this guide) should agree with the unit tests. So if something fails to work as advertised, check what the tests say - and optionally file an issue on GitHub so that the documentation can be fixed.*

**This document is up-to-date for v0.14.1.**

### Features

[**Bindings**](#bindings)
- [``let``, ``letseq``, ``letrec`` as macros](#let-letseq-letrec-as-macros); proper lexical scoping, no boilerplate.
- [``dlet``, ``dletseq``, ``dletrec``, ``blet``, ``bletseq``, ``bletrec``: decorator versions](#dlet-dletseq-dletrec-blet-bletseq-bletrec-decorator-versions)
- [``let_syntax``, ``abbrev``: syntactic local bindings](#let_syntax-abbrev-syntactic-local-bindings); splice code at macro expansion time.
- [Bonus: barebones ``let``](#bonus-barebones-let): pure AST transformation of ``let`` into a ``lambda``.

[**Sequencing**](#sequencing)
- [``do`` as a macro: stuff imperative code into an expression, *with style*](#do-as-a-macro-stuff-imperative-code-into-an-expression-with-style)

[**Tools for lambdas**](#tools-for-lambdas)
- [``multilambda``: supercharge your lambdas](#multilambda-supercharge-your-lambdas); multiple expressions, local variables.
- [``namedlambda``: auto-name your lambdas](#namedlambda-auto-name-your-lambdas) by assignment.
- [``quicklambda``: combo with ``macropy.quick_lambda``](#quicklambda-combo-with-macropyquick_lambda)
- [``envify``: make formal parameters live in an unpythonic ``env``](#envify-make-formal-parameters-live-in-an-unpythonic-env)

[**Language features**](#language-features)
- [``curry``: automatic currying for Python](#curry-automatic-currying-for-python)
- [``lazify``: call-by-need for Python](#lazify-call-by-need-for-python)
  - [Forcing promises manually](#forcing-promises-manually)
  - [Binding constructs and auto-lazification](#binding-constructs-and-auto-lazification)
  - [Note about TCO](#note-about-tco)
- [``tco``: automatic tail call optimization for Python](#tco-automatic-tail-call-optimization-for-python)
  - [TCO and continuations](#tco-and-continuations)
- [``continuations``: call/cc for Python](#continuations-callcc-for-python)
  - [Differences between ``call/cc`` and certain other language features](#differences-between-callcc-and-certain-other-language-features) (generators, exceptions)
  - [``call_cc`` API reference](#call_cc-api-reference)
  - [Combo notes](#combo-notes)
  - [Continuations as an escape mechanism](#continuations-as-an-escape-mechanism)
  - [What can be used as a continuation?](#what-can-be-used-as-a-continuation)
  - [This isn't ``call/cc``!](#this-isnt-callcc)
  - [Why this syntax?](#why-this-syntax)
- [``prefix``: prefix function call syntax for Python](#prefix-prefix-function-call-syntax-for-python)
- [``autoreturn``: implicit ``return`` in tail position](#autoreturn-implicit-return-in-tail-position), like in Lisps.
- [``forall``: nondeterministic evaluation](#forall-nondeterministic-evaluation) with monadic do-notation for Python.

[**Convenience features**](#convenience-features)
- [``cond``: the missing ``elif`` for ``a if p else b``](#cond-the-missing-elif-for-a-if-p-else-b)
- [``aif``: anaphoric if](#aif-anaphoric-if), the test result is ``it``.
- [``autoref``: implicitly reference attributes of an object](#autoref-implicitly-reference-attributes-of-an-object)
- [``dbg``: debug-print expressions with source code](#dbg-debug-print-expressions-with-source-code)

[**Other**](#other)
- [``nb``: silly ultralight math notebook](#nb-silly-ultralight-math-notebook)

[**Meta**](#meta)
- [The xmas tree combo](#the-xmas-tree-combo): notes on the macros working together.

## Bindings

Macros that introduce new ways to bind identifiers.

### ``let``, ``letseq``, ``letrec`` as macros

Properly lexically scoped ``let`` constructs, no boilerplate:

```python
from unpythonic.syntax import macros, let, letseq, letrec

let((x, 17),  # parallel binding, i.e. bindings don't see each other
    (y, 23))[
      print(x, y)]

letseq((x, 1),  # sequential binding, i.e. Scheme/Racket let*
       (y, x+1))[
         print(x, y)]

letrec((evenp, lambda x: (x == 0) or oddp(x - 1)),  # mutually recursive binding, sequentially evaluated
       (oddp,  lambda x: (x != 0) and evenp(x - 1)))[
         print(evenp(42))]
```

As seen in the examples, the syntax is similar to [``unpythonic.lispylet``](../doc/features.md#lispylet-alternative-syntax). Assignment to variables in the environment is supported via the left-shift syntax ``x << 42``.

The bindings are given as macro arguments as ``((name, value), ...)``, the body goes into the ``[...]``.

#### Alternate syntaxes

The following Haskell-inspired, perhaps more pythonic alternate syntaxes are also available:

```python
let[((x, 21),
     (y, 17),
     (z, 4)) in
    x + y + z]

let[x + y + z,
    where((x, 21),
          (y, 17),
          (z, 4))]
```

These syntaxes take no macro arguments; both the let-body and the bindings are placed inside the same ``[...]``.

<details>
<summary>Semantically, these do the exact same thing as the original lispy syntax: </summary>

>The bindings are evaluated first, and then the body is evaluated with the bindings in place. The purpose of the second variant (the *let-where*) is just readability; sometimes it looks clearer to place the body expression first, and only then explain what the symbols in it mean.
>
>These syntaxes are valid for all **expression forms** of ``let``, namely: ``let[]``, ``letseq[]``, ``letrec[]``, ``let_syntax[]`` and ``abbrev[]``. The decorator variants (``dlet`` et al., ``blet`` et al.) and the block variants (``with let_syntax``, ``with abbrev``) support only the original lispy syntax, because there the body is in any case placed differently.
>
>In the first variant above (the *let-in*), note the bindings block still needs the outer parentheses. This is due to Python's precedence rules; ``in`` binds more strongly than the comma (which makes sense almost everywhere else), so to make it refer to all of the bindings, the bindings block must be parenthesized. If the ``let`` expander complains your code does not look like a ``let`` form and you have used *let-in*, check your parentheses.
>
>In the second variant (the *let-where*), note the comma between the body and ``where``; it is compulsory to make the expression into syntactically valid Python. (It's however semi-easyish to remember, since also English requires the comma for a where-expression.)
</details>

#### Special syntax for one binding

If there is only one binding, to make the syntax more pythonic, the outer parentheses may be omitted in the bindings block of the **expr forms** of:

- ``let``, ``letseq``, ``letrec``
- ``dlet``, ``dletseq``, ``dletrec``, ``blet``, ``bletseq``, ``bletrec``
- ``let_syntax``, ``abbrev``

```python
let(x, 21)[2*x]
let[(x, 21) in 2*x]
let[2*x, where(x, 21)]
```

This is valid also in the *let-in* variant, because there is still one set of parentheses enclosing the bindings block.

This is essentially special-cased in the ``let`` expander. (If interested in the technical details, look at ``unpythonic.syntax.letdoutil.UnexpandedLetView``, which performs the destructuring. See also ``unpythonic.syntax.__init__.let``; MacroPy itself already destructures the original lispy syntax when the macro is invoked.)

#### Multiple expressions in body

The `let` constructs can now use a multiple-expression body. The syntax to activate multiple expression mode is an extra set of brackets around the body ([like in `multilambda`](#multilambda-supercharge-your-lambdas)):

```python
let((x, 1),
    (y, 2))[[  # note extra [
      y << x + y,
      print(y)]]

let[((x, 1),      # v0.12.0+
     (y, 2)) in
    [y << x + y,  # body starts here
     print(y)]]

let[[y << x + y,  # v0.12.0+
     print(y)],   # body ends here
    where((x, 1),
          (y, 2))]
```

The let macros implement this by inserting a ``do[...]`` (see below). In a multiple-expression body, also an internal definition context exists for local variables that are not part of the ``let``; see [``do`` for details](#do-as-a-macro-stuff-imperative-code-into-an-expression-with-style).

Only the outermost set of extra brackets is interpreted as a multiple-expression body. The rest are interpreted as usual, as lists. If you need to return a literal list from a ``let`` form with only one body expression, use three sets of brackets:

```python
let((x, 1),
    (y, 2))[[
      [x, y]]]

let[((x, 1),      # v0.12.0+
     (y, 2)) in
    [[x, y]]]

let[[[x, y]],     # v0.12.0+
    where((x, 1),
          (y, 2))]
```

The outermost brackets delimit the ``let`` form, the middle ones activate multiple-expression mode, and the innermost ones denote a list.

Only brackets are affected; parentheses are interpreted as usual, so returning a literal tuple works as expected:

```python
let((x, 1),
    (y, 2))[
      (x, y)]

let[((x, 1),      # v0.12.0+
     (y, 2)) in
    (x, y)]

let[(x, y),       # v0.12.0+
    where((x, 1),
          (y, 2))]
```

#### Notes

``let`` and ``letrec`` expand into the ``unpythonic.lispylet`` constructs, implicitly inserting the necessary boilerplate: the ``lambda e: ...`` wrappers, quoting variable names in definitions, and transforming ``x`` to ``e.x`` for all ``x`` declared in the bindings. Assignment syntax ``x << 42`` transforms to ``e.set('x', 42)``. The implicit environment parameter ``e`` is actually named using a gensym, so lexically outer environments automatically show through. ``letseq`` expands into a chain of nested ``let`` expressions.

Nesting utilizes the fact that MacroPy3 (as of v1.1.0) expands macros in an inside-out order:

```python
letrec((z, 1))[[
         print(z),
         letrec((z, 2))[
                  print(z)]]]
```

Hence the ``z`` in the inner scope expands to the inner environment's ``z``, which makes the outer expansion leave it alone. (This works by transforming only ``ast.Name`` nodes, stopping recursion when an ``ast.Attribute`` is encountered.)


### ``dlet``, ``dletseq``, ``dletrec``, ``blet``, ``bletseq``, ``bletrec``: decorator versions

Similar to ``let``, ``letseq``, ``letrec``, these sugar the corresponding ``unpythonic.lispylet`` constructs, with the ``dletseq`` and ``bletseq`` constructs existing only as macros (expanding to nested ``dlet`` or ``blet``, respectively).

Lexical scoping is respected; each environment is internally named using a gensym. Nesting is allowed.

Examples:

```python
from unpythonic.syntax import macros, dlet, dletseq, dletrec, blet, bletseq, bletrec

@dlet((x, 0))
def count():
    x << x + 1
    return x
assert count() == 1
assert count() == 2

@dletrec((evenp, lambda x: (x == 0) or oddp(x - 1)),
         (oddp,  lambda x: (x != 0) and evenp(x - 1)))
def f(x):
    return evenp(x)
assert f(42) is True
assert f(23) is False

@dletseq((x, 1),
         (x, x+1),
         (x, x+2))
def g(a):
    return a + x
assert g(10) == 14

# block versions: the def takes no arguments, runs immediately, and is replaced by the return value.
@blet((x, 21))
def result():
    return 2*x
assert result == 42

@bletrec((evenp, lambda x: (x == 0) or oddp(x - 1)),
         (oddp,  lambda x: (x != 0) and evenp(x - 1)))
def result():
    return evenp(42)
assert result is True

@bletseq((x, 1),
         (x, x+1),
         (x, x+2))
def result():
    return x
assert result == 4
```

**CAUTION**: assignment to the let environment uses the syntax ``name << value``, as always with ``unpythonic`` environments. The standard Python syntax ``name = value`` creates a local variable, as usual - *shadowing any variable with the same name from the ``let``*.

The write of a ``name << value`` always occurs to the lexically innermost environment (as seen from the write site) that has that ``name``. If no lexically surrounding environment has that ``name``, *then* the expression remains untransformed, and means a left-shift (if ``name`` happens to be otherwise defined).

**CAUTION**: formal parameters of a function definition, local variables, and any names declared as ``global`` or ``nonlocal`` in a given lexical scope shadow names from the ``let`` environment. Mostly, this applies *to the entirety of that lexical scope*. This is modeled after Python's standard scoping rules.

As an exception to the rule, for the purposes of the scope analysis performed by ``unpythonic.syntax``, creations and deletions *of lexical local variables* take effect from the next statement, and remain in effect for the **lexically** remaining part of the current scope. This allows ``x = ...`` to see the old bindings on the RHS, as well as allows the client code to restore access to a surrounding env's ``x`` (by deleting a local ``x`` shadowing it) when desired.

To clarify, here's a sampling from the unit tests:

```python
@dlet((x, "the env x"))
def f():
    return x
assert f() == "the env x"

@dlet((x, "the env x"))
def f():
    x = "the local x"
    return x
assert f() == "the local x"

@dlet((x, "the env x"))
def f():
    return x
    x = "the unused local x"
assert f() == "the env x"

x = "the global x"
@dlet((x, "the env x"))
def f():
    global x
    return x
assert f() == "the global x"

@dlet((x, "the env x"))
def f():
    x = "the local x"
    del x           # deleting a local, ok!
    return x
assert f() == "the env x"

try:
    x = "the global x"
    @dlet((x, "the env x"))
    def f():
        global x
        del x       # ignored by unpythonic's scope analysis, deletion of globals is too dynamic
        return x    # trying to refer to the deleted global x
    f()
except NameError:
    pass
else:
    assert False, "should have tried to access the deleted global x"
```


### ``let_syntax``, ``abbrev``: syntactic local bindings

Locally splice code at macro expansion time (it's almost like inlining functions):

#### ``let_syntax``

```python
from unpythonic.syntax import macros, let_syntax, block, expr

def verylongfunctionname(x=1):
    return x

# works as an expr macro
y = let_syntax((f, verylongfunctionname))[[  # extra brackets: implicit do in body
                 print(f()),
                 f(5)]]
assert y == 5

y = let_syntax((f(a), verylongfunctionname(2*a)))[[  # template with formal parameter "a"
                 print(f(2)),
                 f(3)]]
assert y == 6

# v0.12.0+
y = let_syntax[((f, verylongfunctionname)) in
               [print(f()),
                f(5)]]
y = let_syntax[[print(f()),
                f(5)],
               where((f, verylongfunctionname))]
y = let_syntax[((f(a), verylongfunctionname(2*a))) in
               [print(f(2)),
                f(3)]]
y = let_syntax[[print(f(2)),
                f(3)],
               where((f(a), verylongfunctionname(2*a)))]

# works as a block macro
with let_syntax:
    with block(a, b, c) as makeabc:  # capture a block of statements
        lst = [a, b, c]
    makeabc(3 + 4, 2**3, 3 * 3)
    assert lst == [7, 8, 9]
    with expr(n) as nth:             # capture a single expression
        lst[n]
    assert nth(2) == 9

with let_syntax:
    with block(a) as twice:
        a
        a
    with block(x, y, z) as appendxyz:
        lst += [x, y, z]
    lst = []
    twice(appendxyz(7, 8, 9))
    assert lst == [7, 8, 9]*2
```

After macro expansion completes, ``let_syntax`` has zero runtime overhead; it completely disappears in macro expansion.

<details>
<summary> There are two kinds of substitutions: </summary>

>*Bare name* and *template*. A bare name substitution has no parameters. A template substitution has positional parameters. (Named parameters, ``*args``, ``**kwargs`` and default values are currently **not** supported.)
>
>When used as an expr macro, the formal parameter declaration is placed where it belongs; on the name side (LHS) of the binding. In the above example, ``f(a)`` is a template with a formal parameter ``a``. But when used as a block macro, the formal parameters are declared on the ``block`` or ``expr`` "context manager" due to syntactic limitations of Python. To define a bare name substitution, just use ``with block as ...:`` or ``with expr as ...:`` with no arguments.
>
>In the body of ``let_syntax``, a bare name substitution is invoked by name (just like a variable). A template substitution is invoked like a function call. Just like in an actual function call, when the template is substituted, any instances of its formal parameters in the definition get replaced by the argument values from the "call" site; but ``let_syntax`` performs this at macro-expansion time, and the "value" is a snippet of code.
>
>Note each instance of the same formal parameter (in the definition) gets a fresh copy of the corresponding argument value. In other words, in the example above, each ``a`` in the body of ``twice`` separately expands to a copy of whatever code was given as the positional argument ``a``.
>
>When used as a block macro, there are furthermore two capture modes: *block of statements*, and *single expression*. (The single expression can be an explicit ``do[]`` if multiple expressions are needed.) When invoking substitutions, keep in mind Python's usual rules regarding where statements or expressions may appear.
>
>(If you know about Python ASTs, don't worry about the ``ast.Expr`` wrapper needed to place an expression in a statement position; this is handled automatically.)
</details>
<p>

**HINT**: If you get a compiler error that some sort of statement was encountered where an expression was expected, check your uses of ``let_syntax``. The most likely reason is that a substitution is trying to splice a block of statements into an expression position.

<details>
 <summary> Expansion of this macro is a two-step process: </summary>

>  - First, template substitutions.
>  - Then, bare name substitutions, applied to the result of the first step.
>
>This design is to avoid accidental substitutions into formal parameters of templates (that would usually break the template, resulting at best in a mysterious error, and at worst silently doing something unexpected), if the name of a formal parameter happens to match one of the currently active bare name substitutions.
>
>Within each step, the substitutions are applied **in definition order**:
>
>  - If the bindings are ``((x, y), (y, z))``, then an ``x`` at the use site transforms to ``z``. So does a ``y`` at the use site.
>  - But if the bindings are ``((y, z), (x, y))``, then an ``x`` at the use site transforms to ``y``, and only an explicit ``y`` at the use site transforms to ``z``.
>
>Even in block templates, arguments are always expressions, because invoking a template uses the function-call syntax. But names and calls are expressions, so a previously defined substitution (whether bare name or an invocation of a template) can be passed as an argument just fine. Definition order is then important; consult the rules above.
</details>
<p>

Nesting ``let_syntax`` is allowed. Lexical scoping is supported (inner definitions of substitutions shadow outer ones).

When used as an expr macro, all bindings are registered first, and then the body is evaluated. When used as a block macro, a new binding (substitution declaration) takes effect from the next statement onward, and remains active for the lexically remaining part of the ``with let_syntax:`` block.

#### `abbrev`

The ``abbrev`` macro is otherwise exactly like ``let_syntax``, but it expands in the first pass (outside in). Hence, no lexically scoped nesting, but it has the power to locally rename also macros, because the ``abbrev`` itself expands before any macros invoked in its body. This allows things like:

```python
abbrev((a, ast_literal))[
         a[tree1] if a[tree2] else a[tree3]]

# v0.12.0+
abbrev[((a, ast_literal)) in
       a[tree1] if a[tree2] else a[tree3]]
abbrev[a[tree1] if a[tree2] else a[tree3],
       where((a, ast_literal))]
```

which can be useful when writing macros.

**CAUTION**: ``let_syntax`` is essentially a toy macro system within the real macro system. The usual caveats of macro systems apply. Especially, we support absolutely no form of hygiene. Be very, very careful to avoid name conflicts.

The ``let_syntax`` macro is meant for simple local substitutions where the elimination of repetition can shorten the code and improve its readability. If you need to do something complex (or indeed save a definition and reuse it somewhere else, non-locally), write a real macro directly in MacroPy.

This was inspired by Racket's [``let-syntax``](https://docs.racket-lang.org/reference/let.html) and [``with-syntax``](https://docs.racket-lang.org/reference/stx-patterns.html).


### Bonus: barebones ``let``

As a bonus, we provide classical simple ``let`` and ``letseq``, wholly implemented as AST transformations, providing true lexical variables but no assignment support (because in Python, assignment is a statement) or multi-expression body support. Just like in Lisps, this version of ``letseq`` (Scheme/Racket ``let*``) expands into a chain of nested ``let`` expressions, which expand to lambdas.

These are provided in the separate module ``unpythonic.syntax.simplelet``, import them with the line:

``from unpythonic.syntax.simplelet import macros, let, letseq``.

## Sequencing

Macros that run multiple expressions, in sequence, in place of one expression.

### ``do`` as a macro: stuff imperative code into an expression, *with style*

We provide an ``expr`` macro wrapper for ``unpythonic.seq.do``, with some extra features.

This essentially allows writing imperative code in any expression position. For an `if-elif-else` conditional, [see `cond`](#cond-the-missing-elif-for-a-if-p-else-b); for loops, see [the functions in `unpythonic.fploop`](../unpythonic/fploop.py) (esp. `looped`).

```python
from unpythonic.syntax import macros, do, local, delete

y = do[local[x << 17],
       print(x),
       x << 23,
       x]
print(y)  # --> 23

a = 5
y = do[local[a << 17],
       print(a),  # --> 17
       delete[a],
       print(a),  # --> 5
       True]
```

Local variables are declared and initialized with ``local[var << value]``, where ``var`` is a bare name. To explicitly denote "no value", just use ``None``.  ``delete[...]`` allows deleting a ``local[...]`` binding. This uses ``env.pop()`` internally, so a ``delete[...]`` returns the value the deleted local variable had at the time of deletion. (So if you manually use the ``do()`` function in some code without macros, feel free to ``env.pop()`` in a do-item if needed.)

A ``local`` declaration comes into effect in the expression following the one where it appears, capturing the declared name as a local variable for the **lexically** remaining part of the ``do``. In a ``local``, the RHS still sees the previous bindings, so this is valid (although maybe not readable):

```python
result = []
let((lst, []))[[result.append(lst),       # the let "lst"
                local[lst << lst + [1]],  # LHS: do "lst", RHS: let "lst"
                result.append(lst)]]      # the do "lst"
assert result == [[], [1]]
```

Already declared local variables are updated with ``var << value``. Updating variables in lexically outer environments (e.g. a ``let`` surrounding a ``do``) uses the same syntax.

<details>
<summary>The reason we require local variables to be declared is to allow write access to lexically outer environments.</summary>

>Assignments are recognized anywhere inside the ``do``; but note that any ``let`` constructs nested *inside* the ``do``, that define variables of the same name, will (inside the ``let``) shadow those of the ``do`` - as expected of lexical scoping.
>
>The necessary boilerplate (notably the ``lambda e: ...`` wrappers) is inserted automatically, so the expressions in a ``do[]`` are only evaluated when the underlying ``seq.do`` actually runs.
>
>When running, ``do`` behaves like ``letseq``; assignments **above** the current line are in effect (and have been performed in the order presented). Re-assigning to the same name later overwrites (this is afterall an imperative tool).
>
>We also provide a ``do0`` macro, which returns the value of the first expression, instead of the last.
</details>
<p>

**CAUTION**: ``do[]`` supports local variable deletion, but the ``let[]`` constructs don't, by design. When ``do[]`` is used implicitly with the extra bracket syntax, any ``delete[]`` refers to the scope of the implicit ``do[]``, not any surrounding ``let[]`` scope.

## Tools for lambdas

Macros that introduce additional features for Python's lambdas.

### ``multilambda``: supercharge your lambdas

**Multiple expressions**: use ``[...]`` to denote a multiple-expression body. The macro implements this by inserting a ``do``.

**Local variables**: available in a multiple-expression body. For details on usage, see ``do``.

```python
from unpythonic.syntax import macros, multilambda, let

with multilambda:
    echo = lambda x: [print(x), x]
    assert echo("hi there") == "hi there"

    count = let((x, 0))[
              lambda: [x << x + 1,  # x belongs to the surrounding let
                       x]]
    assert count() == 1
    assert count() == 2

    test = let((x, 0))[
             lambda: [x << x + 1,
                      local[y << 42],  # y is local to the implicit do
                      (x, y)]]
    assert test() == (1, 42)
    assert test() == (2, 42)

    myadd = lambda x, y: [print("myadding", x, y),
                          local[tmp << x + y],
                          print("result is", tmp),
                          tmp]
    assert myadd(2, 3) == 5

    # only the outermost set of brackets denote a multi-expr body:
    t = lambda: [[1, 2]]
    assert t() == [1, 2]
```

In the second example, returning ``x`` separately is redundant, because the assignment to the let environment already returns the new value, but it demonstrates the usage of multiple expressions in a lambda.


### ``namedlambda``: auto-name your lambdas

Who said lambdas have to be anonymous?

```python
from unpythonic.syntax import macros, namedlambda

with namedlambda:
    f = lambda x: x**3                       # assignment: name as "f"
    assert f.__name__ == "f"
    gn, hn = let((x, 42), (g, None), (h, None))[[
                   g << (lambda x: x**2),    # env-assignment: name as "g"
                   h << f,                   # still "f" (no literal lambda on RHS)
                   (g.__name__, h.__name__)]]
    assert gn == "g"
    assert hn == "f"

    foo = let[(f7, lambda x: x) in f7]       # let-binding: name as "f7"
```

Lexically inside a ``with namedlambda`` block, any literal ``lambda`` that is assigned to a name using one of the supported assignment forms is named to have the name of the LHS of the assignment. The name is captured at macro expansion time.

Decorated lambdas are also supported, as is a ``curry`` (manual or auto) where the last argument is a lambda. The latter is a convenience feature, mainly for applying parametric decorators to lambdas. See [the unit tests](../unpythonic/syntax/test/test_lambdatools.py) for detailed examples.

The naming is performed using the function ``unpythonic.misc.namelambda``, which will return a modified copy with its ``__name__``, ``__qualname__`` and ``__code__.co_name`` changed. The original function object is not mutated.

**Supported assignment forms**:

 - Single-item assignment to a local name, ``f = lambda ...: ...``

 - Expression-assignment to an unpythonic environment, ``f << (lambda ...: ...)``

 - Let bindings, ``let[(f, (lambda ...: ...)) in ...]``, using any let syntax supported by unpythonic (here using the haskelly let-in just as an example).
 - Env-assignments are processed lexically, just like regular assignments.

Support for other forms of assignment may or may not be added in a future version.

### ``quicklambda``: combo with ``macropy.quick_lambda``

To be able to transform correctly, the block macros in ``unpythonic.syntax`` that transform lambdas (e.g. ``multilambda``, ``tco``) need to see all ``lambda`` definitions written with Python's standard ``lambda``. However, the highly useful ``macropy.quick_lambda`` uses the syntax ``f[...]``, which (to the analyzer) does not look like a lambda definition.

This macro changes the expansion order, forcing any ``f[...]`` lexically inside the block to expand in the first pass. Any expression of the form ``f[...]`` (the ``f`` is literal) is understood as a quick lambda, whether or not ``f`` and ``_`` are imported at the call site.

Example - a quick multilambda:

```python
from unpythonic.syntax import macros, multilambda, quicklambda, f, _, local

with quicklambda, multilambda:
    func = f[[local[x << _],
              local[y << _],
              x + y]]
    assert func(1, 2) == 3
```

This is of course rather silly, as an unnamed formal parameter can only be mentioned once. If we're giving names to them, a regular ``lambda`` is shorter to write. A more realistic combo is:

```python
with quicklambda, tco:
    def g(x):
        return 2*x
    func1 = f[g(3*_)]  # tail call
    assert func1(10) == 60

    func2 = f[3*g(_)]  # no tail call
    assert func2(10) == 60
```


### ``envify``: make formal parameters live in an unpythonic ``env``

When a function whose definition (``def`` or ``lambda``) is lexically inside a ``with envify`` block is entered, it copies references to its arguments into an unpythonic ``env``. At macro expansion time, all references to the formal parameters are redirected to that environment. This allows rebinding, from an expression position, names that were originally the formal parameters.

Wherever could *that* be useful? For an illustrative caricature, consider [PG's accumulator puzzle](http://paulgraham.com/icad.html).

The modern pythonic solution:

```python
def foo(n):
    def accumulate(i):
        nonlocal n
        n += i
        return n
    return accumulate
```

This avoids allocating an extra place to store the accumulator ``n``. If you want optimal bytecode, this is the best solution in Python 3.

But what if, instead, we consider the readability of the unexpanded source code? The definition of ``accumulate`` requires many lines for something that simple. What if we wanted to make it a lambda? Because all forms of assignment are statements in Python, the above solution is not admissible for a lambda, even with macros.

So if we want to use a lambda, we have to create an ``env``, so that we can write into it. Let's use the let-over-lambda idiom:

```python
def foo(n0):
    return let[(n, n0) in
               (lambda i: n << n + i)]
```

Already better, but the ``let`` is used only for (in effect) altering the passed-in value of ``n0``; we don't place any other variables into the ``let`` environment. Considering the source text already introduces an ``n0`` which is just used to initialize ``n``, that's an extra element that could be eliminated.

Enter the ``envify`` macro, which automates this:

```python
with envify:
    def foo(n):
        return lambda i: n << n + i
```

Combining with ``autoreturn`` yields the fewest-elements optimal solution to the accumulator puzzle:

```python
with autoreturn, envify:
    def foo(n):
        lambda i: n << n + i
```

The ``with`` block adds a few elements, but if desired, it can be refactored into the definition of a custom dialect in [Pydialect](https://github.com/Technologicat/pydialect).

## Language features

To boldly go where Python without macros just won't. Changing the rules by code-walking and making significant rewrites.

### ``curry``: automatic currying for Python

```python
from unpythonic.syntax import macros, curry
from unpythonic import foldr, composerc as compose, cons, nil

with curry:
    def add3(a, b, c):
        return a + b + c
    assert add3(1)(2)(3) == 6
    assert add3(1, 2)(3) == 6
    assert add3(1)(2, 3) == 6
    assert add3(1, 2, 3) == 6

    mymap = lambda f: foldr(compose(cons, f), nil)
    double = lambda x: 2 * x
    print(mymap(double, (1, 2, 3)))

# The definition was auto-curried, so this works here too.
assert add3(1)(2)(3) == 6
```

*Lexically* inside a ``with curry`` block:

 - All **function calls** and **function definitions** (``def``, ``lambda``) are automatically curried, somewhat like in Haskell, or in ``#lang`` [``spicy``](https://github.com/Technologicat/spicy).

 - Function calls are autocurried, and run ``unpythonic.fun.curry`` in a special mode that no-ops on uninspectable functions (triggering a standard function call with the given args immediately) instead of raising ``TypeError`` as usual.

**CAUTION**: Some built-ins are uninspectable or may report their arities incorrectly; in those cases, ``curry`` may fail, occasionally in mysterious ways. The function ``unpythonic.arity.arities``, which ``unpythonic.fun.curry`` internally uses, has a workaround for the inspectability problems of all built-ins in the top-level namespace (as of Python 3.7), but e.g. methods of built-in types are not handled.

Manual uses of the `curry` decorator (on both `def` and `lambda`) are detected, and in such cases the macro skips adding the decorator.

### ``lazify``: call-by-need for Python

Also known as *lazy functions*. Like [lazy/racket](https://docs.racket-lang.org/lazy/index.html), but for Python. Note if you want *lazy sequences* instead, Python already provides those; just use the generator facility (and decorate your gfunc with ``unpythonic.gmemoize`` if needed).

Lazy function example:

```python
with lazify:
    def my_if(p, a, b):
        if p:
            return a  # b never evaluated in this code path
        else:
            return b  # a never evaluated in this code path
    assert my_if(True, 23, 1/0) == 23
    assert my_if(False, 1/0, 42) == 42

    def g(a, b):
        return a
    def f(a, b):
        return g(2*a, 3*b)
    assert f(21, 1/0) == 42
```

In a ``with lazify`` block, function arguments are evaluated only when actually used, at most once each, and in the order in which they are actually used. Promises are automatically forced on access. Automatic lazification applies to arguments in function calls and to let-bindings, since they play a similar role. **No other binding forms are auto-lazified.**

Automatic lazification uses the ``lazyrec[]`` macro (see below), which recurses into certain types of container literals, so that the lazification will not interfere with unpacking.

Note ``my_if`` in the example is a run-of-the-mill runtime function, not a macro. Only the ``with lazify`` is imbued with any magic. Essentially, the above code expands into:

```python
from macropy.quick_lambda import macros, lazy
from unpythonic.syntax import force

def my_if(p, a, b):
    if force(p):
        return force(a)
    else:
        return force(b)
assert my_if(lazy[True], lazy[23], lazy[1/0]) == 23
assert my_if(lazy[False], lazy[1/0], lazy[42]) == 42

def g(a, b):
    return force(a)
def f(a, b):
    return g(lazy[2*force(a)], lazy[3*force(b)])
assert f(lazy[21], lazy[1/0]) == 42
```

plus some clerical details to allow mixing lazy and strict code. This second example relies on the magic of closures to capture f's ``a`` and ``b`` into the promises.

Like ``with continuations``, no state or context is associated with a ``with lazify`` block, so lazy functions defined in one block may call those defined in another.

Lazy code is allowed to call strict functions and vice versa, without requiring any additional effort.

Comboing with other block macros in ``unpythonic.syntax`` is supported, including ``curry`` and ``continuations``. See the [meta](#meta) section of this README for the correct ordering.

For more details, see the docstring of ``unpythonic.syntax.lazify``.

See also ``unpythonic.syntax.lazyrec``, which can be used to lazify expressions inside container literals, recursively. This allows code like ``tpl = lazyrec[(1*2*3, 4*5*6)]``. Each item becomes wrapped with ``lazy[]``, but the container itself is left alone, to avoid interfering with unpacking. Because ``lazyrec[]`` is a macro and must work by names only, it supports a fixed set of container types: ``list``, ``tuple``, ``set``, ``dict``, ``frozenset``, ``unpythonic.collections.frozendict``, ``unpythonic.collections.box``, and ``unpythonic.llist.cons`` (specifically, the constructors ``cons``, ``ll`` and ``llist``).

(It must work by names only, because in an eager language any lazification must be performed as a syntax transformation before the code actually runs. Lazification in an eager language is a hack, by necessity. [Fexprs](https://fexpr.blogspot.com/2011/04/fexpr.html) (along with [a new calculus to go with them](http://fexpr.blogspot.com/2014/03/continuations-and-term-rewriting-calculi.html)) would be a much more elegant approach, but this requires redesigning the whole language from ground up. Of course, if you're fine with a language not particularly designed for extensibility, and lazy evaluation is your top requirement, just use Haskell.)

Inspired by Haskell, Racket's ``(delay)`` and ``(force)``, and [lazy/racket](https://docs.racket-lang.org/lazy/index.html).

**CAUTION**: The functions in ``unpythonic.fun`` are lazify-aware (so that e.g. ``curry`` and ``compose`` work with lazy functions), as are ``call`` and ``callwith`` in ``unpythonic.misc``, but a large part of ``unpythonic`` is not. Keep in mind that any call to a strict (regular Python) function will evaluate all of its arguments.

#### Forcing promises manually

This is mainly useful if you ``lazy[]`` or ``lazyrec[]`` something explicitly, and want to compute its value outside a ``with lazify`` block.

We provide the functions ``force1`` and ``force``. Using ``force1``, if ``x`` is a MacroPy ``lazy[]`` promise, it will be forced, and the resulting value is returned. If ``x`` is not a promise, ``x`` itself is returned, à la Racket. The function ``force``, in addition, descends into containers (recursively). When an atom ``x`` (i.e. anything that is not a container) is encountered, it is processed using ``force1``.

Mutable containers are updated in-place; for immutables, a new instance is created, but as a side effect the promise objects **in the input container** will be forced. Any container with a compatible ``collections.abc`` is supported. (See ``unpythonic.collections.mogrify`` for details.) In addition, as special cases ``unpythonic.collections.box`` and ``unpythonic.llist.cons`` are supported.

#### Binding constructs and auto-lazification

Why do we auto-lazify in certain kinds of binding constructs, but not in others? Function calls and let-bindings have one feature in common: both are guaranteed to bind only new names. Auto-lazification of all assignments, on the other hand, in a language that allows mutation is dangerous, because then this superficially innocuous code will fail:

```python
a = 10
a = 2*a
print(a)  # 20, right?
```

If we chose to auto-lazify assignments, then assuming a ``with lazify`` around the example, it would expand to:

```python
from macropy.quick_lambda import macros, lazy
from unpythonic.syntax import force

a = lazy[10]
a = lazy[2*force(a)]
print(force(a))
```

In the second assignment, the ``lazy[]`` sets up a promise, which will force ``a`` *at the time when the containing promise is forced*, but at that time the name ``a`` points to a promise, which will force...

The fundamental issue is that ``a = 2*a`` is an imperative update. Therefore, to avoid this infinite loop trap for the unwary, assignments are not auto-lazified. Note that if we use two different names, this works just fine:

```python
from macropy.quick_lambda import macros, lazy
from unpythonic.syntax import force

a = lazy[10]
b = lazy[2*force(a)]
print(force(b))
```

because now at the time when ``b`` is forced, the name ``a`` still points to the value we intended it to.

If you're sure you have *new definitions* and not *imperative updates*, just manually use ``lazy[]`` (or ``lazyrec[]``, as appropriate) on the RHS. Or if it's fine to use eager evaluation, just omit the ``lazy[]``, thus allowing Python to evaluate the RHS immediately.

Beside function calls (which bind the parameters of the callee to the argument values of the call) and assignments, there are many other binding constructs in Python. For a full list, see [here](http://excess.org/article/2014/04/bar-foo/), or locally [here](../unpythonic/syntax/scoping.py), in function ``get_names_in_store_context``. Particularly noteworthy in the context of lazification are the ``for`` loop and the ``with`` context manager.

In Python's ``for``, the loop counter is an imperatively updated single name. In many use cases a rapid update is desirable for performance reasons, and in any case, the whole point of the loop is (almost always) to read the counter (and do something with the value) at least once per iteration. So it is much simpler, faster, and equally correct not to lazify there.

In ``with``, the whole point of a context manager is that it is eagerly initialized when the ``with`` block is entered (and finalized when the block exits). Since our lazy code can transparently use both bare values and promises (due to the semantics of our ``force1``), and the context manager would have to be eagerly initialized anyway, we can choose not to lazify there.

#### Note about TCO

To borrow a term from PG's On Lisp, to make ``lazify`` *pay-as-you-go*, a special mode in ``unpythonic.tco.trampolined`` is automatically enabled by ``with lazify`` to build lazify-aware trampolines in order to avoid a drastic performance hit (~10x) in trampolines built for regular strict code.

The idea is that the mode is enabled while any function definitions in the ``with lazify`` block run, so they get a lazify-aware trampoline when the ``trampolined`` decorator is applied. This should be determined lexically, but that's complicated to do API-wise, so we currently enable the mode for the dynamic extent of the ``with lazify``. Usually this is close enough; the main case where this can behave unexpectedly is:

```python
@trampolined  # strict trampoline
def g():
    ...

def make_f():
    @trampolined  # which kind of trampoline is this?
    def f():
        ...
    return f

f1 = make_f()  # f1 gets the strict trampoline

with lazify:
    @trampolined  # lazify-aware trampoline
    def h():
        ...

    f2 = make_f()  # f2 gets the lazify-aware trampoline
```

TCO chains with an arbitrary mix of lazy and strict functions should work as long as the first function in the chain has a lazify-aware trampoline, because the chain runs under the trampoline of the first function (the trampolines of any tail-called functions are stripped away by the TCO machinery).

Tail-calling from a strict function into a lazy function should work, because all arguments are evaluated at the strict side before the call is made.

But tail-calling ``strict -> lazy -> strict`` will fail in some cases. The second strict callee may get promises instead of values, because the strict trampoline does not have the ``lazycall`` (the mechanism ``with lazify`` uses to force the args when lazy code calls into strict code).

The reason we have this hack is that it allows the performance of strict code using unpythonic's TCO machinery, not even caring that a ``lazify`` exists, to be unaffected by the additional machinery used to support automatic lazy-strict interaction.


### ``tco``: automatic tail call optimization for Python

```python
from unpythonic.syntax import macros, tco

with tco:
    evenp = lambda x: (x == 0) or oddp(x - 1)
    oddp  = lambda x: (x != 0) and evenp(x - 1)
    assert evenp(10000) is True

with tco:
    def evenp(x):
        if x == 0:
            return True
        return oddp(x - 1)
    def oddp(x):
        if x != 0:
            return evenp(x - 1)
        return False
    assert evenp(10000) is True
```

All function definitions (``def`` and ``lambda``) lexically inside the block undergo TCO transformation. The functions are automatically ``@trampolined``, and any tail calls in their return values are converted to ``jump(...)`` for the TCO machinery. Here *return value* is defined as:

 - In a ``def``, the argument expression of ``return``, or of a call to a known escape continuation.

 - In a ``lambda``, the whole body, as well as the argument expression of a call to a known escape continuation.

What is a *known escape continuation* is explained below, in the section [TCO and ``call_ec``](#tco-and-call-ec).

To find the tail position inside a compound return value, this recursively handles any combination of ``a if p else b``, ``and``, ``or``; and from ``unpythonic.syntax``, ``do[]``, ``let[]``, ``letseq[]``, ``letrec[]``. Support for ``do[]`` includes also any ``multilambda`` blocks that have already expanded when ``tco`` is processed. The macros ``aif[]`` and ``cond[]`` are also supported, because they expand into a combination of ``let[]``, ``do[]``, and ``a if p else b``.

**CAUTION**: In an ``and``/``or`` expression, only the last item of the whole expression is in tail position. This is because in general, it is impossible to know beforehand how many of the items will be evaluated.

**CAUTION**: In a ``def`` you still need the ``return``; it marks a return value. If you want the tail position to imply a ``return``, use the combo ``with autoreturn, tco`` (on ``autoreturn``, see below).

TCO is based on a strategy similar to MacroPy's ``tco`` macro, but using unpythonic's TCO machinery, and working together with the macros introduced by ``unpythonic.syntax``. The semantics are slightly different; by design, ``unpythonic`` requires an explicit ``return`` to mark tail calls in a ``def``. A call that is strictly speaking in tail position, but lacks the ``return``, is not TCO'd, and Python's implicit ``return None`` then shuts down the trampoline, returning ``None`` as the result of the TCO chain.

#### TCO and continuations

The ``tco`` macro detects and skips any ``with continuations`` blocks inside the ``with tco`` block, because ``continuations`` already implies TCO. This is done **for the specific reason** of allowing the [Lispython dialect](https://github.com/Technologicat/pydialect) to use ``with continuations``, because the dialect itself implies a ``with tco`` for the whole module (so the user code has no way to exit the TCO context).

The ``tco`` and ``continuations`` macros actually share a lot of the code that implements TCO; ``continuations`` just hooks into some callbacks to perform additional processing.

#### TCO and ``call_ec``

(Mainly of interest for lambdas, which have no ``return``, and for "multi-return" from a nested function.)

It is important to recognize a call to an escape continuation as such, because the argument given to an escape continuation is essentially a return value. If this argument is itself a call, it needs the TCO transformation to be applied to it.

For escape continuations in ``tco`` and ``continuations`` blocks, only basic uses of ``call_ec`` are supported, for automatically harvesting names referring to an escape continuation. In addition, the literal function names ``ec`` and ``brk`` are always *understood as referring to* an escape continuation.

The name ``ec`` or ``brk`` alone is not sufficient to make a function into an escape continuation, even though ``tco`` (and ``continuations``) will think of it as such. The function also needs to actually implement some kind of an escape mechanism. An easy way to get an escape continuation, where this has already been done for you, is to use ``call_ec``.

See the docstring of ``unpythonic.syntax.tco`` for details.


### ``continuations``: call/cc for Python

*Where control flow is your playground.*

If you're new to continuations, see the [short and easy Python-based explanation](https://www.ps.uni-saarland.de/~duchier/python/continuations.html) of the basic idea.

We provide a very loose pythonification of Paul Graham's continuation-passing macros, chapter 20 in [On Lisp](http://paulgraham.com/onlisp.html).

The approach differs from native continuation support (such as in Scheme or Racket) in that the continuation is captured only where explicitly requested with ``call_cc[]``. This lets most of the code work as usual, while performing the continuation magic where explicitly desired.

As a consequence of the approach, our continuations are *delimited* in the very crude sense that the captured continuation ends at the end of the body where the *currently dynamically outermost* ``call_cc[]`` was used. Hence, if porting some code that uses ``call/cc`` from Racket to Python, in the Python version the ``call_cc[]`` may be need to be placed further out to capture the relevant part of the computation. For example, see ``amb`` in the demonstration below; a Scheme or Racket equivalent usually has the ``call/cc`` placed inside the ``amb`` operator itself, whereas in Python we must place the ``call_cc[]`` at the call site of ``amb``.

For various possible program topologies that continuations may introduce, see [these clarifying pictures](callcc_topology.pdf).

For full documentation, see the docstring of ``unpythonic.syntax.continuations``. The unit tests [[1]](../unpythonic/syntax/test/test_conts.py) [[2]](../unpythonic/syntax/test/test_conts_escape.py) [[3]](../unpythonic/syntax/test/test_conts_gen.py) [[4]](../unpythonic/syntax/test/test_conts_topo.py) may also be useful as usage examples.

**Note on debugging**: If a function containing a ``call_cc[]`` crashes below the ``call_cc[]``, the stack trace will usually have the continuation function somewhere in it, containing the line number information, so you can pinpoint the source code line where the error occurred. (For a function ``f``, it is named ``f_cont``, ``f_cont1``, ...) But be aware that especially in complex macro combos (e.g. ``continuations, curry, lazify``), the other block macros may spit out many internal function calls *after* the relevant stack frame that points to the actual user program. So check the stack trace as usual, but check further up than usual.

Demonstration:

```python
from unpythonic.syntax import macros, continuations, call_cc

with continuations:
    # basic example - how to call a continuation manually:
    k = None  # kontinuation
    def setk(*args, cc):
        global k
        k = cc
        return args
    def doit():
        lst = ['the call returned']
        *more, = call_cc[setk('A')]
        return lst + list(more)
    print(doit())
    print(k('again'))
    print(k('thrice', '!'))

    # McCarthy's amb operator - yes, the real thing - in Python:
    stack = []
    def amb(lst, cc):
        if not lst:
            return fail()
        first, *rest = tuple(lst)
        if rest:
            ourcc = cc
            stack.append(lambda: amb(rest, cc=ourcc))
        return first
    def fail():
        if stack:
            f = stack.pop()
            return f()

    # Pythagorean triples
    def pt():
        z = call_cc[amb(range(1, 21))]
        y = call_cc[amb(range(1, z+1)))]
        x = call_cc[amb(range(1, y+1))]
        if x*x + y*y != z*z:
            return fail()
        return x, y, z
    print(pt())
    print(fail())  # ...outside the dynamic extent of pt()!
    print(fail())
    print(fail())
    print(fail())
    print(fail())
    print(fail())
```
Code within a ``with continuations`` block is treated specially.
<details>
 <summary>Roughly:</summary>

> - Each function definition (``def`` or ``lambda``) in a ``with continuations`` block has an implicit formal parameter ``cc``, **even if not explicitly declared** in the formal parameter list.
>   - The continuation machinery will set the default value of ``cc`` to the default continuation (``identity``), which just returns its arguments.
>     - The default value allows these functions to be called also normally without passing a ``cc``. In effect, the function will then return normally.
>   - If ``cc`` is not declared explicitly, it is implicitly declared as a by-name-only parameter named ``cc``, and the default value is set automatically.
>   - If ``cc`` is declared explicitly, the default value is set automatically if ``cc`` is in a position that can accept a default value, and no default has been set by the user.
>     - Positions that can accept a default value are the last positional parameter that has no default, and a by-name-only parameter in any syntactically allowed position.
>   - Having a hidden parameter is somewhat magic, but overall improves readability, as this allows declaring ``cc`` only where actually explicitly needed.
>     - **CAUTION**: Usability trap: in nested function definitions, each ``def`` and ``lambda`` comes with **its own** implicit ``cc``.
>       - In the above ``amb`` example, the local variable is named ``ourcc``, so that the continuation passed in from outside (into the ``lambda``, by closure) will have a name different from the ``cc`` implicitly introduced by the ``lambda`` itself.
>       - This is possibly subject to change in a future version (pending the invention of a better API), but for now just be aware of this gotcha.
>   - Beside ``cc``, there's also a mechanism to keep track of the captured tail of a computation, which is important to have edge cases work correctly. See the note on **pcc** (*parent continuation*) in the docstring of ``unpythonic.syntax.continuations``, and [the pictures](callcc_topology.pdf).
>
> - In a function definition inside the ``with continuations`` block:
>   - Most of the language works as usual; especially, any non-tail function calls can be made as usual.
>   - ``return value`` or ``return v0, ..., vn`` is actually a tail-call into ``cc``, passing the given value(s) as arguments.
>     - As in other parts of ``unpythonic``, returning a tuple means returning multiple-values.
>       - This is important if the return value is received by the assignment targets of a ``call_cc[]``. If you get a ``TypeError`` concerning the arguments of a function with a name ending in ``_cont``, check your ``call_cc[]`` invocations and the ``return`` in the call_cc'd function.
>   - ``return func(...)`` is actually a tail-call into ``func``, passing along (by default) the current value of ``cc`` to become its ``cc``.
>     - Hence, the tail call is inserted between the end of the current function body and the start of the continuation ``cc``.
>     - To override which continuation to use, you can specify the ``cc=...`` kwarg, as in ``return func(..., cc=mycc)``.
>       - The ``cc`` argument, if passed explicitly, **must be passed by name**.
>         - **CAUTION**: This is **not** enforced, as the machinery does not analyze positional arguments in any great detail. The machinery will most likely break in unintuitive ways (or at best, raise a mysterious ``TypeError``) if this rule is violated.
>     - The function ``func`` must be a defined in a ``with continuations`` block, so that it knows what to do with the named argument ``cc``.
>       - Attempting to tail-call a regular function breaks the TCO chain and immediately returns to the original caller (provided the function even accepts a ``cc`` named argument).
>       - Be careful: ``xs = list(args); return xs`` and ``return list(args)`` mean different things.
>   - TCO is automatically applied to these tail calls. This uses the exact same machinery as the ``tco`` macro.
>
> - The ``call_cc[]`` statement essentially splits its use site into *before* and *after* parts, where the *after* part (the continuation) can be run a second and further times, by later calling the callable that represents the continuation. This makes a computation resumable from a desired point.
>   - The continuation is essentially a closure.
>   - Just like in Scheme/Racket, only the control state is checkpointed by ``call_cc[]``; any modifications to mutable data remain.
>   - Assignment targets can be used to get the return value of the function called by ``call_cc[]``.
>   - Just like in Scheme/Racket's ``call/cc``, the values that get bound to the ``call_cc[]`` assignment targets on second and further calls (when the continuation runs) are the arguments given to the continuation when it is called (whether implicitly or manually).
>   - A first-class reference to the captured continuation is available in the function called by ``call_cc[]``, as its ``cc`` argument.
>     - The continuation is a function that takes positional arguments, plus a named argument ``cc``.
>       - The call signature for the positional arguments is determined by the assignment targets of the ``call_cc[]``.
>       - The ``cc`` parameter is there only so that a continuation behaves just like any continuation-enabled function when tail-called, or when later used as the target of another ``call_cc[]``.
>   - Basically everywhere else, ``cc`` points to the identity function - the default continuation just returns its arguments.
>     - This is unlike in Scheme or Racket, which implicitly capture the continuation at every expression.
>   - Inside a ``def``, ``call_cc[]`` generates a tail call, thus terminating the original (parent) function. (Hence ``call_ec`` does not combo well with this.)
>   - At the top level of the ``with continuations`` block, ``call_cc[]`` generates a normal call. In this case there is no return value for the block (for the continuation, either), because the use site of the ``call_cc[]`` is not inside a function.
</details>

#### Differences between ``call/cc`` and certain other language features

 - Unlike **generators**, ``call_cc[]`` allows resuming also multiple times from an earlier checkpoint, even after execution has already proceeded further. Generators can be easily built on top of ``call/cc``. [Python version](../unpythonic/syntax/test/test_conts_gen.py), [Racket version](https://github.com/Technologicat/python-3-scicomp-intro/blob/master/examples/beyond_python/generator.rkt).
   - The Python version is a pattern that could be packaged into a macro with MacroPy; the Racket version has been packaged as a macro.
   - Both versions are just demonstrations for teaching purposes. In production code, use the language's native functionality.
     - Python's built-in generators have no restriction on where ``yield`` can be placed, and provide better performance.
     - Racket's standard library provides [generators](https://docs.racket-lang.org/reference/Generators.html).

 - Unlike **exceptions**, which only perform escapes, ``call_cc[]`` allows to jump back at an arbitrary time later, also after the dynamic extent of the original function where the ``call_cc[]`` appears. Escape continuations are a special case of continuations, so exceptions can be built on top of ``call/cc``.
   - [As explained in detail by Matthew Might](http://matt.might.net/articles/implementing-exceptions/), exceptions are fundamentally based on (escape) continuations; the *"unwinding the call stack"* mental image is ["not even wrong"](https://en.wikiquote.org/wiki/Wolfgang_Pauli).

#### ``call_cc`` API reference

To keep things relatively straightforward, our ``call_cc[]`` is only allowed to appear **at the top level** of:

  - the ``with continuations`` block itself
  - a ``def`` or ``async def``

Nested defs are ok; here *top level* only means the top level of the *currently innermost* ``def``.

If you need to place ``call_cc[]`` inside a loop, use ``@looped`` et al. from ``unpythonic.fploop``; this has the loop body represented as the top level of a ``def``.

Multiple ``call_cc[]`` statements in the same function body are allowed. These essentially create nested closures.

**Syntax**:

In ``unpythonic``, ``call_cc`` is a **statement**, with the following syntaxes:

```python
x = call_cc[func(...)]
*xs = call_cc[func(...)]
x0, ... = call_cc[func(...)]
x0, ..., *xs = call_cc[func(...)]
call_cc[func(...)]

x = call_cc[f(...) if p else g(...)]
*xs = call_cc[f(...) if p else g(...)]
x0, ... = call_cc[f(...) if p else g(...)]
x0, ..., *xs = call_cc[f(...) if p else g(...)]
call_cc[f(...) if p else g(...)]
```

*NOTE*: ``*xs`` may need to be written as ``*xs,`` in order to explicitly make the LHS into a tuple. The variant without the comma seems to work when run with [the bootstrapper](macropy3) from a ``.py``, but fails in code run interactively in [the IPython+MacroPy console](https://github.com/azazel75/macropy/pull/20).

*NOTE*: ``f()`` and ``g()`` must be **literal function calls**. Sneaky trickery (such as calling indirectly via ``unpythonic.misc.call`` or ``unpythonic.fun.curry``) is not supported. (The ``prefix`` and ``curry`` macros, however, **are** supported; just order the block macros as shown in the final section of this README.) This limitation is for simplicity; the ``call_cc[]`` needs to patch the ``cc=...`` kwarg of the call being made.

**Assignment targets**:

 - To destructure a multiple-values (from a tuple return value), use a tuple assignment target (comma-separated names, as usual).

 - The last assignment target may be starred. It is transformed into the vararg (a.k.a. ``*args``, star-args) of the continuation function. (It will capture a whole tuple, or any excess items, as usual.)

 - To ignore the return value, just omit the assignment part. Useful if ``func`` was called only to perform its side-effects (the classic side effect is to stash ``cc`` somewhere for later use).

**Conditional variant**:

 - ``p`` is any expression. If truthy, ``f(...)`` is called, and if falsey, ``g(...)`` is called.

 - Each of ``f(...)``, ``g(...)`` may be ``None``. A ``None`` skips the function call, proceeding directly to the continuation. Upon skipping, all assignment targets (if any are present) are set to ``None``. The starred assignment target (if present) gets the empty tuple.

The main use case of the conditional variant is for things like:

```python
with continuations:
   k = None
   def setk(cc):
       global k
       k = cc
   def dostuff(x):
       call_cc[setk() if x > 10 else None]  # update stashed continuation only if x > 10
       ...
```

**Main differences to ``call/cc`` in Scheme and Racket**:

Compared to Scheme/Racket, where ``call/cc`` will capture also expressions occurring further up in the call stack, our ``call_cc`` may be need to be placed differently (further out, depending on what needs to be captured) due to the delimited nature of the continuations implemented here.

Scheme and Racket implicitly capture the continuation at every position, whereas we do it explicitly, only at the use sites of the ``call_cc[]`` macro.

Also, since there are limitations to where a ``call_cc[]`` may appear, some code may need to be structured differently to do some particular thing, if porting code examples originally written in Scheme or Racket.

Unlike ``call/cc`` in Scheme/Racket, our ``call_cc`` takes **a function call** as its argument, not just a function reference. Also, there's no need for it to be a one-argument function; any other args can be passed in the call. The ``cc`` argument is filled implicitly and passed by name; any others are passed exactly as written in the client code.

#### Combo notes

**CAUTION**: Do not use ``with tco`` inside a ``with continuations`` block; ``continuations`` already implies TCO. The ``continuations`` macro **makes no attempt** to skip ``with tco`` blocks inside it.

If you need both ``continuations`` and ``multilambda`` simultaneously, the incantation is:

```python
with multilambda, continuations:
    f = lambda x: [print(x), x**2]
    assert f(42) == 1764
```

This works, because the ``continuations`` macro understands already expanded ``let[]`` and ``do[]``, and ``multilambda`` generates and expands a ``do[]``. (Any explicit use of ``do[]`` in a lambda body or in a ``return`` is also ok; recall that macros expand from inside out.)

Similarly, if you need ``quicklambda``, apply it first:

```python
with quicklambda, continuations:
    g = f[_**2]
    assert g(42) == 1764
```

This ordering makes the ``f[...]`` notation expand into standard ``lambda`` notation before ``continuations`` is expanded.

To enable both of these, use ``with quicklambda, multilambda, continuations`` (although the usefulness of this combo may be questionable).

#### Continuations as an escape mechanism

Pretty much by the definition of a continuation, in a ``with continuations`` block, a trick that *should* at first glance produce an escape is to set ``cc`` to the ``cc`` of the caller, and then return the desired value. There is however a subtle catch, due to the way we implement continuations.

First, consider this basic strategy, without any macros:

```python
from unpythonic import call_ec

def double_odd(x, ec):
    if x % 2 == 0:  # reject even "x"
        ec("not odd")
    return 2*x
@call_ec
def result1(ec):
    y = double_odd(42, ec)
    z = double_odd(21, ec)
    return z
@call_ec
def result2(ec):
    y = double_odd(21, ec)
    z = double_odd(42, ec)
    return z
assert result1 == "not odd"
assert result2 == "not odd"
```

Now, can we use the same strategy with the continuation machinery?

```python
from unpythonic.syntax import macros, continuations, call_cc

with continuations:
    def double_odd(x, ec, cc):
        if x % 2 == 0:
            cc = ec
            return "not odd"
        return 2*x
    def main1(cc):
        # cc actually has a default, so it's ok to not pass anything as cc here.
        y = double_odd(42, ec=cc)  # y = "not odd"
        z = double_odd(21, ec=cc)  # we could tail-call, but let's keep this similar to the first example.
        return z
    def main2(cc):
        y = double_odd(21, ec=cc)
        z = double_odd(42, ec=cc)
        return z
    assert main1() == 42
    assert main2() == "not odd"
```

In the first example, ``ec`` is the escape continuation of the ``result1``/``result2`` block, due to the placement of the ``call_ec``. In the second example, the ``cc`` inside ``double_odd`` is the implicitly passed ``cc``... which, naively, should represent the continuation of the current call into ``double_odd``. So far, so good.

However, because the example code contains no ``call_cc[]`` statements, the actual value of ``cc``, anywhere in this example, is always just ``identity``. *It's not the actual continuation.* Even though we pass the ``cc`` of ``main1``/``main2`` as an explicit argument "``ec``" to use as an escape continuation (like the first example does with ``ec``), it is still ``identity`` - and hence cannot perform an escape.

We must ``call_cc[]`` to request a capture of the actual continuation:

```python
from unpythonic.syntax import macros, continuations, call_cc

with continuations:
    def double_odd(x, ec, cc):
        if x % 2 == 0:
            cc = ec
            return "not odd"
        return 2*x
    def main1(cc):
        y = call_cc[double_odd(42, ec=cc)]  # <-- the only change is adding the call_cc[]
        z = call_cc[double_odd(21, ec=cc)]  # <--
        return z
    def main2(cc):
        y = call_cc[double_odd(21, ec=cc)]  # <--
        z = call_cc[double_odd(42, ec=cc)]  # <--
        return z
    assert main1() == "not odd"
    assert main2() == "not odd"
```

This variant performs as expected.

There's also a second, even subtler catch; instead of setting ``cc = ec`` and returning a value, just tail-calling ``ec`` with that value doesn't do what we want. This is because - as explained in the rules of the ``continuations`` macro, above - a tail-call is *inserted* between the end of the function, and whatever ``cc`` currently points to.

Most often that's exactly what we want, but in this particular case, it causes *both* continuations to run, in sequence. But if we overwrite ``cc``, then the function's original ``cc`` argument (the one given by ``call_cc[]``) is discarded, so it never runs - and we get the effect we want, *replacing* the ``cc`` by the ``ec``.

Such subtleties arise essentially from the difference between a language that natively supports continuations (Scheme, Racket) and one that has continuations hacked on top of it as macros performing a CPS conversion only partially (like Python with ``unpythonic.syntax``, or Common Lisp with PG's continuation-passing macros). The macro approach works, but the programmer needs to be careful.

#### What can be used as a continuation?

In ``unpythonic`` specifically, a continuation is just a function. ([As John Shutt has pointed out](http://fexpr.blogspot.com/2014/03/continuations-and-term-rewriting-calculi.html), in general this is not true. The calculus underlying the language becomes much cleaner if continuations are defined as a separate control flow mechanism orthogonal to function application. Continuations are not intrinsically a whole-computation device, either.)

The continuation function must be able to take as many positional arguments as the previous function in the TCO chain is trying to pass into it. Keep in mind that:

 - In ``unpythonic``, a tuple represents multiple return values. So a ``return a, b``, which is being fed into the continuation, implies that the continuation must be able to take two positional arguments.

 - At the end of any function in Python, at least an implicit bare ``return`` always exists. It will try to pass in the value ``None`` to the continuation, so the continuation must be able to accept one positional argument. (This is handled automatically for continuations created by ``call_cc[]``. If no assignment targets are given, ``call_cc[]`` automatically creates one ignored positional argument that defaults to ``None``.)

If there is an arity mismatch, Python will raise ``TypeError`` as usual. (The actual error message may be unhelpful due to the macro transformations; look for a mismatch in the number of values between a ``return`` and the call signature of a function used as a continuation (most often, the ``f`` in a ``cc=f``).)

Usually, a function to be used as a continuation is defined inside the ``with continuations`` block. This automatically introduces the implicit ``cc`` parameter, and in general makes the source code undergo the transformations needed by the continuation machinery.

However, as the only exception to this rule, if the continuation is meant to act as the endpoint of the TCO chain - i.e. terminating the chain and returning to the original top-level caller - then it may be defined outside the ``with continuations`` block. Recall that in a ``with continuations`` block, returning an inert data value (i.e. not making a tail call) transforms into a tail-call into the ``cc`` (with the given data becoming its argument(s)); it does not set the ``cc`` argument of the continuation being called, or even require that it has a ``cc`` parameter that could accept one.

(Note also that a continuation that has no ``cc`` parameter cannot be used as the target of an explicit tail-call in the client code, since a tail-call in a ``with continuations`` block will attempt to supply a ``cc`` argument to the function being tail-called. Likewise, it cannot be used as the target of a ``call_cc[]``, since this will also attempt to supply a ``cc`` argument.)

These observations make ``unpythonic.fun.identity`` eligible as a continuation, even though it is defined elsewhere in the library and it has no ``cc`` parameter.

#### This isn't ``call/cc``!

Strictly speaking, ``True``. The implementation is very different (much more than just [exposing a hidden parameter](https://www.ps.uni-saarland.de/~duchier/python/continuations.html)), not to mention it has to be a macro, because it triggers capture - something that would not need to be requested for separately, had we converted the whole program into [CPS](https://en.wikipedia.org/wiki/Continuation-passing_style).

The selective capture approach is however more efficient when we implement the continuation system in Python, indeed *on Python* (in the sense of [On Lisp](paulgraham.com/onlisp.html)), since we want to run most of the program the usual way with no magic attached. This way there is no need to sprinkle absolutely every statement and expression with a ``def`` or a ``lambda``. (Not to mention Python's ``lambda`` is underpowered due to the existence of some language features only as statements, so we would need to use a mixture of both, which is already unnecessarily complicated.) Function definitions are not intended as [the only control flow construct](https://dspace.mit.edu/handle/1721.1/5753) in Python, so the compiler likely wouldn't optimize heavily enough (i.e. eliminate **almost all** of the implicitly introduced function definitions), if we attempted to use them as such.

Continuations only need to come into play when we explicitly request for one ([ZoP §2](https://www.python.org/dev/peps/pep-0020/)); this avoids introducing any more extra function definitions than needed.

The name is nevertheless ``call_cc``, because the resulting behavior is close enough to ``call/cc``.

Is it as general? I'm not an expert on this. If you have a theoretical result that proves that continuations delimited in the (very crude) way they are in ``unpythonic`` are equally powerful to classic ``call/cc``, or a counterexample that shows they aren't, I'm interested - this information should be in the README. (Note that beside the delimited capture, we provide a kludge that allows manually overriding ``cc``, useful for implementing things like ``amb``.)

Racket provides properly delimited continuations and [prompts](https://docs.racket-lang.org/guide/prompt.html) to control them; no doubt much more thought has gone into designing and implementing *that*.

#### Why this syntax?

As for a function call in ``call_cc[...]`` vs. just a function reference: Typical lispy usage of ``call/cc`` uses an inline lambda, with the closure property passing in everything except ``cc``, but in Python ``def`` is a statement. A technically possible alternative syntax would be:

```python
with call_cc(f):  # this syntax not supported!
    def f(cc):
        ...
```

but the expr macro variant provides better options for receiving multiple return values, and perhaps remains closer to standard Python.

The ``call_cc[]`` explicitly suggests that these are (almost) the only places where the ``cc`` argument obtains a non-default value. It also visually indicates the exact position of the checkpoint, while keeping to standard Python syntax.

(*Almost*: As explained above, a tail call passes along the current value of ``cc``, and ``cc`` can be set manually.)



### ``prefix``: prefix function call syntax for Python

Write Python almost like Lisp!

Lexically inside a ``with prefix`` block, any literal tuple denotes a function call, unless quoted. The first element is the operator, the rest are arguments. Bindings of the ``let`` macros and the top-level tuple in a ``do[]`` are left alone, but ``prefix`` recurses inside them (in the case of bindings, on each RHS).

The rest is best explained by example:

```python
from unpythonic.syntax import macros, prefix, q, u, kw
from unpythonic import apply

with prefix:
    (print, "hello world")

    # quote operator q locally turns off the function-call transformation:
    t1 = (q, 1, 2, (3, 4), 5)  # q takes effect recursively
    x = 42
    t2 = (q, 17, 23, x)  # unlike in Lisps, x refers to its value even in a quote
    (print, t1, t2)

    # unquote operator u locally turns the transformation back on:
    t3 = (q, (u, print, 42), (print, 42), "foo", "bar")
    assert t3 == (q, None, (print, 42), "foo", "bar")

    # quotes nest; call transformation made when quote level == 0
    t4 = (q, (print, 42), (q, (u, u, print, 42)), "foo", "bar")
    assert t4 == (q, (print, 42), (None,), "foo", "bar")

    # Be careful:
    try:
        (x,)  # in a prefix block, this means "call the 0-arg function x"
    except TypeError:
        pass  # 'int' object is not callable
    (q, x)  # OK!

    # give named args with kw(...) [it's syntax, not really a function!]:
    def f(*, a, b):
        return (q, a, b)
    # in one kw(...), or...
    assert (f, kw(a="hi there", b="Tom")) == (q, "hi there", "Tom")
    # in several kw(...), doesn't matter
    assert (f, kw(a="hi there"), kw(b="Tom")) == (q, "hi there", "Tom")
    # in case of duplicate name across kws, rightmost wins
    assert (f, kw(a="hi there"), kw(b="Tom"), kw(b="Jerry")) == (q, "hi there", "Jerry")

    # give *args with unpythonic.fun.apply, like in Lisps:
    lst = [1, 2, 3]
    def g(*args):
        return args
    assert (apply, g, lst) == (q, 1, 2, 3)
    # lst goes last; may have other args first
    assert (apply, g, "hi", "ho", lst) == (q, "hi" ,"ho", 1, 2, 3)
```

This comboes with ``curry`` for an authentic *LisThEll* programming experience:

```python
from unpythonic.syntax import macros, curry, prefix, q, u, kw
from unpythonic import foldr, composerc as compose, cons, nil

with prefix, curry:  # important: apply prefix first, then curry
    mymap = lambda f: (foldr, (compose, cons, f), nil)
    double = lambda x: 2 * x
    (print, (mymap, double, (q, 1, 2, 3)))
    assert (mymap, double, (q, 1, 2, 3)) == ll(2, 4, 6)
```

**CAUTION**: The ``prefix`` macro is experimental and not intended for use in production code.


### ``autoreturn``: implicit ``return`` in tail position

In Lisps, a function implicitly returns the value of the expression in tail position (along the code path being executed). Python's ``lambda`` also behaves like this (the whole body is just one return-value expression), but ``def`` doesn't.

Now ``def`` can, too:

```python
from unpythonic.syntax import macros, autoreturn

with autoreturn:
    def f():
        ...
        "I'll just return this"
    assert f() == "I'll just return this"

    def g(x):
        ...
        if x == 1:
            "one"
        elif x == 2:
            "two"
        else:
            "something else"
    assert g(1) == "one"
    assert g(2) == "two"
    assert g(42) == "something else"
```

Each ``def`` function definition lexically within the ``with autoreturn`` block is examined, and if the last item within the body is an expression ``expr``, it is transformed into ``return expr``. Additionally:

 - If the last item is an ``if``/``elif``/``else`` block, the transformation is applied to the last item in each of its branches.

 - If the last item is a ``with`` or ``async with`` block, the transformation is applied to the last item in its body.

 - If the last item is a ``try``/``except``/``else``/``finally`` block:
   - **If** an ``else`` clause is present, the transformation is applied to the last item in it; **otherwise**, to the last item in the ``try`` clause. These are the positions that indicate a normal return (no exception was raised).
   - In both cases, the transformation is applied to the last item in each of the ``except`` clauses.
   - The ``finally`` clause is not transformed; the intention is it is usually a finalizer (e.g. to release resources) that runs after the interesting value is already being returned by ``try``, ``else`` or ``except``.

If needed, the above rules are applied recursively to locate the tail position(s).

Any explicit ``return`` statements are left alone, so ``return`` can still be used as usual.

**CAUTION**: If the final ``else`` of an ``if``/``elif``/``else`` is omitted, as often in Python, then only the ``else`` item is in tail position with respect to the function definition - likely not what you want. So with ``autoreturn``, the final ``else`` should be written out explicitly, to make the ``else`` branch part of the same ``if``/``elif``/``else`` block.

**CAUTION**: ``for``, ``async for``, ``while`` are currently not analyzed; effectively, these are defined as always returning ``None``. If the last item in your function body is a loop, use an explicit return.

**CAUTION**: With ``autoreturn`` enabled, functions no longer return ``None`` by default; the whole point of this macro is to change the default return value. The default return value is ``None`` only if the tail position contains a statement other than ``if``, ``with``, ``async with`` or ``try``.

If you wish to omit ``return`` in tail calls, this comboes with ``tco``; just apply ``autoreturn`` first (either ``with autoreturn, tco:`` or in nested format, ``with tco:``, ``with autoreturn:``).


### ``forall``: nondeterministic evaluation

Behaves the same as the multiple-body-expression tuple comprehension ``unpythonic.amb.forall``, but implemented purely by AST transformation, with real lexical variables. This is essentially a MacroPy implementation of Haskell's do-notation for Python, specialized to the List monad (but the code is generic and very short; see ``unpythonic.syntax.forall``).

```python
from unpythonic.syntax import macros, forall, insist, deny

out = forall[y << range(3),
             x << range(3),
             insist(x % 2 == 0),
             (x, y)]
assert out == ((0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2))

# pythagorean triples
pt = forall[z << range(1, 21),   # hypotenuse
            x << range(1, z+1),  # shorter leg
            y << range(x, z+1),  # longer leg
            insist(x*x + y*y == z*z),
            (x, y, z)]
assert tuple(sorted(pt)) == ((3, 4, 5), (5, 12, 13), (6, 8, 10),
                             (8, 15, 17), (9, 12, 15), (12, 16, 20))
```

Assignment (with List-monadic magic) is ``var << iterable``. It is only valid at the top level of the ``forall`` (e.g. not inside any possibly nested ``let``).

``insist`` and ``deny`` are not really macros; they are just the functions from ``unpythonic.amb``, re-exported for convenience.

The error raised by an undefined name in a ``forall`` section is ``NameError``.


## Convenience features

Small macros that are not essential but make some things easier or simpler.

### ``cond``: the missing ``elif`` for ``a if p else b``

Now lambdas too can have multi-branch conditionals, yet remain human-readable:

```python
from unpythonic.syntax import macros, cond

answer = lambda x: cond[x == 2, "two",
                        x == 3, "three",
                        "something else"]
print(answer(42))
```

Syntax is ``cond[test1, then1, test2, then2, ..., otherwise]``. Expansion raises an error if the ``otherwise`` branch is missing.

Any part of ``cond`` may have multiple expressions by surrounding it with brackets:

```python
cond[[pre1, ..., test1], [post1, ..., then1],
     [pre2, ..., test2], [post2, ..., then2],
     ...
     [postn, ..., otherwise]]
```

To denote a single expression that is a literal list, use an extra set of brackets: ``[[1, 2, 3]]``.


### ``aif``: anaphoric if

This is mainly of interest as a point of [comparison with Racket](https://github.com/Technologicat/python-3-scicomp-intro/blob/master/examples/beyond_python/aif.rkt); ``aif`` is about the simplest macro that relies on either the lack of hygiene or breaking thereof.

```python
from unpythonic.syntax import macros, aif

aif[2*21,
    print("it is {}".format(it)),
    print("it is falsey")]
```

Syntax is ``aif[test, then, otherwise]``. The magic identifier ``it`` refers to the test result while (lexically) inside the ``aif``, and does not exist outside the ``aif``.

Any part of ``aif`` may have multiple expressions by surrounding it with brackets (implicit ``do[]``):

```python
aif[[pre, ..., test],
    [post_true, ..., then],        # "then" branch
    [post_false, ..., otherwise]]  # "otherwise" branch
```

To denote a single expression that is a literal list, use an extra set of brackets: ``[[1, 2, 3]]``.


### ``autoref``: implicitly reference attributes of an object

Ever wish you could ``with(obj)`` to say ``x`` instead of ``obj.x`` to read attributes of an object? Enter the ``autoref`` block macro:

```python
from unpythonic.syntax import macros, autoref
from unpythonic import env

e = env(a=1, b=2)
c = 3
with autoref(e):
    assert a == 1  # a --> e.a
    assert b == 2  # b --> e.b
    assert c == 3  # no c in e, so just c
```

The transformation is applied for names in ``Load`` context only, including names found in ``Attribute`` or ``Subscript`` nodes.

Names in ``Store`` or ``Del`` context are not redirected. To write to or delete attributes of ``o``, explicitly refer to ``o.x``, as usual.

Nested autoref blocks are allowed (lookups are lexically scoped).

Reading with ``autoref`` can be convenient e.g. for data returned by [SciPy's ``.mat`` file loader](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.loadmat.html).

See the [unit tests](../unpythonic/syntax/test/test_autoref.py) for more usage examples.


### ``dbg``: debug-print expressions with source code

[DRY](https://en.wikipedia.org/wiki/Don't_repeat_yourself) out your [qnd](https://en.wiktionary.org/wiki/quick-and-dirty) debug printing code. Both block and expression variants are provided:

```python
from unpythonic.syntax import macros, dbg

with dbg:
    x = 2
    print(x)   # --> [file.py:5] x: 2

with dbg:
    x = 2
    y = 3
    print(x, y, 17 + 23)   # --> [file.py:10] x: 2, y: 3, (17 + 23): 40
    print(x, y, 17 + 23, sep="\n")   # --> [file.py:11] x: 2
                                     #     [file.py:11] y: 3
                                     #     [file.py:11] (17 + 23): 40

z = dbg[25 + 17]  # --> [file.py:15] (25 + 17): 42
assert z == 42    # surrounding an expression with dbg[...] doesn't alter its value
```

**In the block variant**, just like in ``nb``, a custom print function can be supplied as the first positional argument. This avoids transforming any uses of built-in ``print``:

```python
prt = lambda *args, **kwargs: print(*args)

with dbg(prt):
    x = 2
    prt(x)     # --> ('x',) (2,)
    print(x)   # --> 2

with dbg(prt):
    x = 2
    y = 17
    prt(x, y, 1 + 2)  # --> ('x', 'y', '(1 + 2)'), (2, 17, 3)

```

The reference to the custom print function (i.e. the argument to the ``dbg`` block) **must be a bare name**. Support for methods may or may not be added in a future version.

**In the expr variant**, to customize printing, just assign another function to the name ``dbgprint_expr`` (locally or globally, as desired). A default implementation is provided and automatically injected to the namespace of the module that imports anything from ``unpythonic.syntax`` (see ``expose_unhygienic`` in MacroPy).

For details on implementing custom debug print functions, see the docstrings of ``unpythonic.syntax.dbgprint_block`` and ``unpythonic.syntax.dbgprint_expr``, which provide the default implementations.

**CAUTION**: The source code is back-converted from the AST representation; hence its surface syntax may look slightly different to the original (e.g. extra parentheses). See ``macropy.core.unparse``.

**CAUTION**: ``dbg`` only works in ``.py`` files, not in [the IPython+MacroPy console](https://github.com/azazel75/macropy/pull/20), because the expanded code refers to ``__file__``, which is not defined in the REPL. This limitation may or may not be lifted in a future version.

Inspired by the [dbg macro in Rust](https://doc.rust-lang.org/std/macro.dbg.html).

## Other

Stuff that didn't fit elsewhere.

### ``nb``: silly ultralight math notebook

Mix regular code with math-notebook-like code in a ``.py`` file. To enable notebook mode, ``with nb``:

```python
from unpythonic.syntax import macros, nb
from sympy import symbols, pprint

with nb:
    2 + 3
    assert _ == 5
    _ * 42
    assert _ == 210

with nb(pprint):
    x, y = symbols("x, y")
    x * y
    assert _ == x * y
    3 * _
    assert _ == 3 * x * y
```

Expressions at the top level auto-assign the result to ``_``, and auto-print it if the value is not ``None``. Only expressions do that; for any statement that is not an expression, ``_`` retains its previous value.

A custom print function can be supplied as the first positional argument to ``nb``. This is useful with SymPy (and [latex-input](https://github.com/clarkgrubb/latex-input) to use α, β, γ, ... as actual variable names).

Obviously not intended for production use, although is very likely to work anywhere.

## Meta

Is this just a set of macros, a language extension, or a compiler for a new language that just happens to be implemented in MacroPy, à la *On Lisp*? All of the above, really.

See our [notes on comboability](../doc/design-notes.md#comboability).

### The xmas tree combo

The macros in ``unpythonic.syntax`` are designed to work together, but some care needs to be taken regarding the order in which they expand.

The block macros are designed to run **in the following order (leftmost first)**:

```
prefix > autoreturn, quicklambda > multilambda > continuations or tco > ...
                                                    ... > curry > namedlambda, autoref > lazify > envify
```

The ``let_syntax`` (and ``abbrev``) block may be placed anywhere in the chain; just keep in mind what it does.

The ``dbg`` block can be run at any position after ``prefix`` and before ``tco`` (or ``continuations``). (It must be able to see regular function calls.)

For simplicity, **the block macros make no attempt to prevent invalid combos** (unless there is a specific technical reason to do that for some particular combination). Be careful; e.g. don't nest several ``with tco`` blocks (lexically), that won't work.

Example combo in the single-line format:

```python
with autoreturn, tco, lazify:
    ...
```

In the multiline format:

```python
with lazify:
  with tco:
    with autoreturn:
      ...
```

See our [notes on macros](../doc/design-notes.md#notes-on-macros) for more information.
