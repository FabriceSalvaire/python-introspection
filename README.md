**This repository contains the code to perform the introspection of a Python module using Python 3.15.**

**Note:** This code could be a Python tutorial about this topic.

Over time, Python is becoming increasingly complicated...  For example, annotations and `if
TYPE_CHECKING:` make things more complicated than they used to be.  Moreover the corresponding Python
documentation is hard to grasp!  And there are several ways to go about it...

**The targeted audiences are to :**
- generate stub `.pyi` files
- extract docstrings and API
- or curiosity

**WARNING :** This code is closely linked to the Python version since the annotation language
feature is not yet stable...

## Design

**Since Python is a dynamic language**, this code load (execute) the module to perform
introspection.  The `autodoc2` static approach doesn't make sense for Python!  Since it will not be
able to discover things that are dynamically generated, e.g. using `setattr`.  Indeed, we can do
funky things with Python...  However, this implementation also load the AST to discover things which
are not *actually* available through the Python introspection API.

There are several ways to handle `if TYPE_CHECKING:`, `sphinx.ext.autodoc` tries to load the module
with `TYPE_CHECKING = True` but it can fails...  This implementation uses the AST to find
`doc_comments` and type checking's imports.

## Dependencies 

This code requires these dependencies :
- [ast-comments](https://github.com/t3rn0/ast-comments) An extension to the built-in **ast** module
  to finds comments in source code and adds them to the parsed tree. (should be a buitin feature...)
- [rich](https://github.com/textualize/rich) for beautiful formatting in the terminal

## Relevant Projects

- [sphinx.ext.autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
  Builtin Sphinx extension to include documentation from docstrings. (It is a Sphinx soup...)
- [sphinx-autodoc2](https://github.com/sphinx-extensions2/sphinx-autodoc2) A Sphinx extension that
  automatically generates API documentation for your Python packages. (This package seems no longer
  maintained and has design issues...)

## Relevant Python Documentation

- [annotationlib - Functionality for introspecting annotations — Python Documentation](https://docs.python.org/fr/3/library/annotationlib.html)
- [ast - Abstract syntax trees — Python Documentation](https://docs.python.org/fr/3/library/ast.html)
- [inspect - Inspect live objects — Python Documentation](https://docs.python.org/fr/3/library/inspect.html)
- [token - Constants used with Python parse trees — Python Documentation](https://docs.python.org/fr/3/library/token.html)
- [types - Dynamic type creation and names for built-in types — Python documentation](https://docs.python.org/3/library/types.html)
- [typing - Support for type hints — Python Documentation](https://docs.python.org/fr/3/library/typing.html)
