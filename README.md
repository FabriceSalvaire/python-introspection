**This repository contains the code to perform the introspection of a Python module using Python 3.15.**

Over time, Python is becoming increasingly complicated...  For example, annotations and `if
TYPE_CHECKING:` make things more complicated than they used to be.  Moreover the relevant Python
documentation is hard to digest !  And there is several ways to do things...

**Note:** This code could be a Python tutorial about this topic.

**The targeted audiences are to :**
- generate stub `.pyi` files
- extract docstrings and API
- or curiosity

This code requires these dependencies :
- [ast-comments](https://github.com/t3rn0/ast-comments)
  An extension to the built-in **ast** module to finds comments in source code and adds them to the parsed tree. (should be a buitin feature...)
- [rich](https://github.com/textualize/rich) for beautiful formatting in the terminal

# Relevant Projects

- [sphinx.ext.autodoc](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
  Builtin Sphinx extension to include documentation from docstrings.
- [sphinx-autodoc2](https://github.com/sphinx-extensions2/sphinx-autodoc2)
  A Sphinx extension that automatically generates API documentation for your Python packages.

# Relevant Python Documentation

- [annotationlib - Functionality for introspecting annotations — Python Documentation](https://docs.python.org/fr/3/library/annotationlib.html)
- [ast - Abstract syntax trees — Python Documentation](https://docs.python.org/fr/3/library/ast.html)
- [inspect - Inspect live objects — Python Documentation](https://docs.python.org/fr/3/library/inspect.html)
- [token - Constants used with Python parse trees — Python Documentation](https://docs.python.org/fr/3/library/token.html)
- [types - Dynamic type creation and names for built-in types — Python documentation](https://docs.python.org/3/library/types.html)
- [typing - Support for type hints — Python Documentation](https://docs.python.org/fr/3/library/typing.html)
