# Unpythonic: Python meets Lisp and Haskell

In the spirit of [toolz](https://github.com/pytoolz/toolz), we provide missing features for Python, mainly from the list processing tradition, but with some Haskellisms mixed in. We place a special emphasis on **clear, pythonic syntax**. These features make up the pure-Python core of `unpythonic`, and are meant to be used directly. We also provide extensions to the Python language as a set of [syntactic macros](https://en.wikipedia.org/wiki/Macro_(computer_science)#Syntactic_macros) that are designed to work together. Each macro adds an orthogonal piece of functionality that can (mostly) be mixed and matched with the others.

The macros provide an extension to the pure-Python layer, and offers features such as *automatic* currying, *automatic* tail-call optimization, lexically scoped ``let`` and ``do`` with lean syntax, and implicit return statements. Some of these macro features, like call-by-need (lazy functions), continuations (``call/cc``), and easy-to-use multi-expression lambdas with local variables, are not available in the pure-Python layer. Additionally, some pure-Python features like batteries for itertools do not have a macro layer equivalent. Check the [documentation](#documentation) for the full sets of features.

The design considerations of `unpythonic` are based in simplicity, robustness, and with minimal dependencies. See our [design notes](doc/design-notes.md) for more information.

### Dependencies

Currently none required.  
[MacroPy](https://github.com/azazel75/macropy) optional, to enable the syntactic macro layer.

### Documentation

[Pure-Python feature set](doc/features.md)  
[Syntactic macro feature set](macro_extras/README.md): the second half of ``unpythonic``.  
[Design notes](doc/design-notes.md): for more insight into the design choices of ``unpythonic``

## Installation

**PyPI**

``pip3 install unpythonic --user``

or

``sudo pip3 install unpythonic``

**GitHub**

Clone (or pull) from GitHub. Then,

``python3 setup.py install --user``

or

``sudo python3 setup.py install``

**Uninstall**

Uninstallation must be invoked in a folder which has no subfolder called ``unpythonic``, so that ``pip`` recognizes it as a package name (instead of a filename). Then,

``pip3 uninstall unpythonic``

or

``sudo pip3 uninstall unpythonic``

## License

2-clause [BSD](LICENSE.md).

Dynamic assignment based on [StackOverflow answer by Jason Orendorff (2010)](https://stackoverflow.com/questions/2001138/how-to-create-dynamical-scoped-variables-in-python), used under CC-BY-SA. The threading support is original to our version.

Core idea of ``lispylet`` based on [StackOverflow answer by divs1210 (2017)](https://stackoverflow.com/a/44737147), used under the MIT license.

Core idea of ``view`` based on [StackOverflow answer by Mathieu Caroff (2018)](https://stackoverflow.com/a/53253136), used under the MIT license. Our additions include support for sequences with changing length, write support, iteration based on ``__iter__``, in-place reverse, and the abstract base classes.


## Acknowledgements

Thanks to [TUT](http://www.tut.fi/en/home) for letting me teach [RAK-19006 in spring term 2018](https://github.com/Technologicat/python-3-scicomp-intro); early versions of parts of this library were originally developed as teaching examples for that course. Thanks to @AgenttiX for feedback.

The trampoline implementation of ``unpythonic.tco`` takes its remarkably clean and simple approach from ``recur.tco`` in [fn.py](https://github.com/fnpy/fn.py). Our main improvements are a cleaner syntax for the client code, and the addition of the FP looping constructs.

Another important source of inspiration was [tco](https://github.com/baruchel/tco) by Thomas Baruchel, for thinking about the possibilities of TCO in Python.

## Python-related FP resources

Python clearly wants to be an impure-FP language. A decorator with arguments *is a curried closure* - how much more FP can you get?

- [Awesome Functional Python](https://github.com/sfermigier/awesome-functional-python), especially a list of useful libraries. Some picks:

  - [fn.py: Missing functional features of fp in Python](https://github.com/fnpy/fn.py) (actively maintained fork). Includes e.g. tail call elimination by trampolining, and a very compact way to recursively define infinite streams.

  - [more-itertools: More routines for operating on iterables, beyond itertools.](https://github.com/erikrose/more-itertools)

  - [boltons: Like builtins, but boltons.](https://github.com/mahmoud/boltons) Includes yet more itertools, and much more.

  - [toolz: A functional standard library for Python](https://github.com/pytoolz/toolz)

  - [funcy: A fancy and practical functional tools](https://github.com/suor/funcy/)

  - [pyrsistent: Persistent/Immutable/Functional data structures for Python](https://github.com/tobgu/pyrsistent)

- [List of languages that compile to Python](https://github.com/vindarel/languages-that-compile-to-python) including Hy, a Lisp (in the [Lisp-2](https://en.wikipedia.org/wiki/Lisp-1_vs._Lisp-2) family) that can use Python libraries.

Old, but interesting:

- [Peter Norvig (2000): Python for Lisp Programmers](http://www.norvig.com/python-lisp.html)

- [David Mertz (2001): Charming Python - Functional programming in Python, part 2](https://www.ibm.com/developerworks/library/l-prog2/index.html)
