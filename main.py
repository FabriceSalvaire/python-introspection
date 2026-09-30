####################################################################################################
#
# Introspection of a Python module
# Copyright (C) 2026 Fabrice SALVAIRE
# SPDX-License-Identifier: AGPL-3.0-or-later
#
####################################################################################################

####################################################################################################

import annotationlib
import argparse
import importlib.util
import inspect
import os
import sys
import types
import typing
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

# https://github.com/t3rn0/ast-comments
# import ast
import ast_comments as ast
import rich.console
from rich import markup
from rich.padding import Padding
from rich.text import Text

####################################################################################################

def E(obj: Any) -> str:
    return markup.escape(str(obj))


class Console:

    ##############################################

    def __init__(self) -> None:
        self._console = rich.console.Console()
        self._indent_level = 0
        self._indent_multiplier = 4
        self._lines = []
        self._linesep = os.linesep

    ##############################################

    def print_(self, *args, **kwargs) -> None:
        self._console.print(*args, **kwargs)

    ##############################################

    def flush(self) -> None:
        for line in self._lines:
            match line:
                case Text():
                    # Fixme: we lost pretty...
                    level = self._indent_level * self._indent_multiplier
                    _ = Padding.indent(line, level)
                    self._console.print(_)
                case str():
                    level = self._indent_level * self._indent_multiplier
                    self._console.print(level * ' ' + line)
                case None:
                    self._console.print()
                case _:
                    self._console.print(line)
        self._lines = []

    ##############################################

    def indent(self, level: int = 1) -> None:
        self.flush()
        self._indent_level = max(self._indent_level + level, 0)

    def dedent(self, level: int = 1) -> None:
        self.flush()
        self.indent(-level)

    ##############################################

    def line(self, text: str = '', style: str = '') -> None:
        match text:
            case '':
                _ = None
            case str():
                # Fixme: we lost pretty...
                _ = text  # Text.from_markup(text, style=style)
        self._lines.append(_)

    def line_obj(self, obj: Any) -> None:
        self._lines.append(obj)

    ##############################################

    def rule(self, width: int | None = None, char='─', style: str = '') -> None:
        if width is None:
            width = self._console.width
        self.line(char * width, style=style)


console = Console()

####################################################################################################

def dump_sys_modules() -> None:
    for name in sorted(sys.modules.keys()):
        module = sys.modules[name]
        console.line(f"{name} = {module}")

####################################################################################################

def load_module_from_path(path: Path, module_name: str) -> ModuleType:
    # 1. Create a module spec from the file path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        raise NameError(f"Module not found at {path}")
    # 2. Create a new module based on the spec
    module = importlib.util.module_from_spec(spec)
    # 3. Optional: Add it to sys.modules so imports inside the module work properly
    sys.modules[module_name] = module
    # 4. Execute the module to populate its namespace
    spec.loader.exec_module(module)  # ty: ignore[unresolved-attribute]
    return module

####################################################################################################

# From https://github.com/sphinx-doc/sphinx/pull/14622
def forward_ref_arg(ref: typing.ForwardRef) -> str:
    """Return the source text of a :class:`~typing.ForwardRef`.

    On Python 3.14+, ``annotationlib``'s ``FORWARDREF`` format can store placeholder names like
    ``__annotationlib_name_1__`` in ``__forward_arg__`` when an annotation mixes undefined and
    defined names (e.g. ``Mapping[str, int]`` with ``Mapping`` only imported under
    ``TYPE_CHECKING``).  The real objects are kept in ``__extra_names__``.  Evaluating the reference
    in ``STRING`` format gives the clean text on Python 3.14.5+ (python/cpython#148680);
    substituting ``__extra_names__`` by hand covers earlier 3.14 releases.
    """
    forward_arg: str = ref.__forward_arg__
    if sys.version_info[:2] < (3, 14) or '__annotationlib_name_' not in forward_arg:
        return forward_arg

    try:
        evaluated = ref.evaluate(format=annotationlib.Format.STRING)
    except Exception:  # noqa: BLE001
        evaluated = forward_arg
    if isinstance(evaluated, str) and '__annotationlib_name_' not in evaluated:
        return evaluated

    # Older 3.14 releases leave the placeholders in; substitute by hand.
    extra_names: dict[str, Any] | None = getattr(ref, '__extra_names__', None)
    if extra_names:
        for name, value in extra_names.items():
            forward_arg = forward_arg.replace(name, annotationlib.type_repr(value))
    return forward_arg


def fix_forward_ref(ref: typing.ForwardRef) -> str:
    forward_arg = ref.__forward_arg__
    for name, value in ref.__extra_names__.items():
        forward_arg = forward_arg.replace(name, annotationlib.type_repr(value))
    return forward_arg

####################################################################################################

@dataclass
class DocComment:
    comment: ast.Comment
    assign: ast.Assign | ast.AnnAssign | None = None

####################################################################################################

@dataclass
class TypeCheckingImport:
    module: str
    name: str
    asname: str | None

    ##############################################

    @property
    def as_or_name(self) -> str:
        return self.asname or self.name

####################################################################################################

class ObjectMixin:

    ##############################################

    def __init__(self, obj) -> None:
        self.obj = obj

    ##############################################

    def print_docstring(self) -> None:
        console.line()
        console.line("[blue]Docstring:")
        console.rule(50)
        if self.obj.__doc__:
            console.line(self.obj.__doc__.rstrip())
        # console.line(inspect.getdoc(self.function))
        console.rule(50)

        # console.line('comment', inspect.getcomments(obj))

####################################################################################################

class FunctionMixin(ObjectMixin):

    TITLE: str = 'function'

    ##############################################

    def __init__(self, function: types.FunctionType, purpose: str | None = None) -> None:
        super().__init__(function)
        self.function = function

        # See https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING
        # If you occasionally need to examine type annotations at runtime which may contain undefined
        # symbols, use annotationlib.get_annotations() with a format parameter of
        # annotationlib.Format.STRING or annotationlib.Format.FORWARDREF to safely retrieve the annotations
        # without raising NameError.

        # console.line(f"{function.__annotations__}")
        # console.line(f"{function.__defaults__}")
        # console.line(f"{function.__kwdefaults__}")

        # try:
        _lines, line_number = inspect.getsourcelines(function)
        title = purpose or self.TITLE.capitalize()
        console.line(f"{title} [blue]{function.__name__}[/] @{line_number}")
        # except TypeError:
        #     # property.getter... is builtin_function_or_method
        #     pass
        console.indent()

        signature = inspect.signature(
            function,
            # for TYPE_CHECKING: NameError: name 'Iterable' is not defined
            annotation_format=annotationlib.Format.STRING,
        )
        console.line()
        console.line(f"[blue]Signature[/]: {function.__name__}{E(signature)}")
        for parameter in signature.parameters.values():
            annotation = parameter.annotation
            assert isinstance(annotation, str) or annotation is inspect._empty
            console.line(f"  - {parameter.kind} [blue]{parameter.name}[/]: {E(parameter.annotation)} = {E(parameter.default)}")
            assert type(parameter.annotation) is str or inspect.Signature.empty
        return_type = signature.return_annotation
        assert type(return_type) is str or inspect.Signature.empty
        console.line(f"  - [blue]return[/]: {E(return_type)}")

        # Retrun {} if any annotation !
        console.line("annotation strings")
        annotations = typing.get_type_hints(function, format=annotationlib.Format.STRING, include_extras=True)
        for name, type_ in annotations.items():
            assert type(type_) is str
            console.line(f"  - [blue]{name}[/]: {E(type_)}")

        # This code can raise...
        # ! annotations = typing.get_type_hints(function, format=annotationlib.Format.VALUE, include_extras=True)

        console.line("annotations")
        annotations = typing.get_type_hints(function, format=annotationlib.Format.FORWARDREF, include_extras=True)
        for name, type_ in annotations.items():
            if isinstance(type_, annotationlib.ForwardRef):
                real_type = fix_forward_ref(type_)
                console.line(f"  - [red]{name}[/] ForwardRef '{E(real_type)}'")
                # ! console.line(type_.__dict__)
                # for _ in dir(type_):
                #     console.line(_, getattr(type_, _))
            else:
                console.line(f"  - [blue]{name}[/] {E(type_)}")
                if hasattr(type_, '__origin__'):
                    console.line(f"      origin from dunder: {E(type_.__origin__)}")
                    console.line(f"      args: {E(type_.__args__)}")
                type_origin = typing.get_origin(type_)
                if type_origin is not None:
                    console.line(f"      origin from typing: {E(type_origin)}")
                    args = typing.get_args(type_)
                    console.line(f"      args: {E(args)}")

        self.print_docstring()

        console.dedent()

####################################################################################################

class ModuleAttributeMixin:

    ##############################################

    def __init__(self, module: Module) -> None:
        self.module = module

####################################################################################################

class Variable:
    pass

###################################################################################################

class Function(ModuleAttributeMixin, FunctionMixin):

    ##############################################

    def __init__(self, module: Module, function: types.FunctionType) -> None:
        ModuleAttributeMixin.__init__(self, module)
        FunctionMixin.__init__(self, function)

####################################################################################################

class ClassAttributeMixin:

    ##############################################

    def __init__(self, klass: Class) -> None:
        self.klass = klass

###################################################################################################

class Method(ClassAttributeMixin, FunctionMixin):

    TITLE: str = 'method'

    ##############################################

    def __init__(self, klass: Class, function: types.FunctionType, purpose: str | None = None) -> None:
        ClassAttributeMixin.__init__(self, klass)
        FunctionMixin.__init__(self, function, purpose)

###################################################################################################

class Property(ClassAttributeMixin, ObjectMixin):

    ##############################################

    def __init__(self, klass: Class, property_: property) -> None:
        ClassAttributeMixin.__init__(self, klass)
        ObjectMixin.__init__(self, property_)

        # _lines, line_number = inspect.getsourcelines(function)
        # @{line_number}
        console.line(f"Property [blue]{property_.__name__}[/]")
        console.indent()

        self.print_docstring()

        # for name in ('getter', 'setter', 'deleter'):
        for name in ('fget', 'fset', 'fdel'):
            function = getattr(property_, name)
            # console.print_(name, function, dir(function))
            if function:
                Method(klass, function, name)

        console.dedent()

####################################################################################################

class Class(ModuleAttributeMixin, ObjectMixin):

    ##############################################

    def __init__(self, module: Module, klass: type) -> None:
        ModuleAttributeMixin.__init__(self, module)
        ObjectMixin.__init__(self, klass)
        self.klass = klass

        _lines, line_number = inspect.getsourcelines(klass)
        console.line(f"Class [blue]{klass.__name__}[/]  @{line_number}")
        console.line()
        console.indent()

        mro = klass.__mro__[1:-1]
        console.line(f"[blue]MRO[/] {mro}")

        self.print_docstring()

        # s0 = set([_[0] for _ in inspect.getmembers(klass)])
        # s1 = set(dir(klass))
        # s2 = set(klass.__dict__.keys())
        # assert not (s0 - s1)
        # console.line(s2)
        # console.line(s0 - s2)

        # for name in dir(klass):
        for name in klass.__dict__:
            if name.startswith('__'):
                continue
            obj = getattr(klass, name)
            console.line()
            console.rule(50)
            if inspect.isfunction(obj):
                method = Method(self, obj)
            elif isinstance(obj, property):
                property_ = Property(self, obj)
            else:
                console.line(f"{name} {obj}")

        console.dedent()

####################################################################################################

class Module:

    SPECIAL_NAMES = {
        '__builtins__',
        '__doc__',
        '__file__',
        '__loader__',
        '__name__',
        '__package__',
        '__spec__',
    }

    ##############################################

    def __init__(self, path: Path) -> None:
        # Find the module name
        path = path.resolve()
        parent = path.parent
        while (parent / '__init__.py').exists():
            parent = parent.parent
        relative_path = path.relative_to(parent)
        module_name = '.'.join(list(relative_path.parent.parts) + [path.stem])
        console.line(f"[red]Load module [blue]{module_name}[/] from [green]{path}")
        module = load_module_from_path(path, module_name)

        # console.rule()
        # console.line(module.__dict__)
        # console.rule()
        # console.line(inspect.getmembers(module))
        # console.rule()
        # console.line(dir(module))

        # Get the module attibutes
        modules_names = set(dir(module)) - self.SPECIAL_NAMES

        # Build the AST for the module
        source = path.read_text()
        module_ast = ast.parse(source, type_comments=True)

        console.line()
        console.line("[red]Module AST:")
        console.rule()
        console.line_obj(ast.dump(module_ast, indent=4))
        console.rule()

        # Get top level and TYPE_CHECKING imports
        self._type_checking_imports: dict[str, TypeCheckingImport] = {}
        imported_name = set()
        for node in ast.iter_child_nodes(module_ast):
            match node:
                case ast.Import() | ast.ImportFrom():
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imported_name.add(name)
                case ast.If():
                    test = node.test
                    if isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING':
                        self._on_type_checking(node)

        # Remove imported attributes
        modules_names -= imported_name

        # Look for doc comments and match the assignation
        console.line()
        console.rule()
        console.line("[red]Doc Comments:")
        doc_comments = {}
        for node in ast.walk(module_ast):
            match node:
                case ast.Comment():
                    if node.value.startswith('#:'):
                        lineno = node.lineno  # ty: ignore[unresolved-attribute]
                        if not node.inline:
                            lineno += 1
                        console.line(f"  {node} @{lineno}")
                        doc_comments[lineno] = DocComment(node)
        for node in ast.walk(module_ast):
            match node:
                case ast.Assign() | ast.AnnAssign():
                    lineno = node.lineno
                    doc_comment = doc_comments.get(lineno)
                    if doc_comment is not None:
                        doc_comment.assign = node
                        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                        assert type(target) is ast.Name
                        console.line()
                        console.line(f"match doc comment for [blue]{target.id}[/]\n  {doc_comment}")
                        # Fixme: more than one target
        console.rule()

        console.line()
        console.rule()
        console.line("[red]module.__doc__")
        if module.__doc__:
            console.line(module.__doc__.strip())
        console.rule()

        console.line()
        console.rule()
        console.line("[red]Module Attributes:")
        console.line(f"Imported: {sorted(imported_name)}")
        console.line(f"Type Checking Imported: {self._type_checking_imports.values()}")
        console.line(f"Defined: {sorted(modules_names)}")

        for name in sorted(modules_names):
            console.line()
            console.rule()
            obj = getattr(module, name)
            if inspect.isclass(obj):
                klass = Class(self, obj)
            elif inspect.isfunction(obj):
                function = Function(self, obj)
            else:
                console.line(f"{name}: {type(obj)} = {obj}")

    ##############################################

    def _on_type_checking(self, if_node: ast.If) -> None:
        console.line()
        console.line(f"[red]Found if TYPE_CHECKING[/] @{if_node.lineno}")
        for node in ast.iter_child_nodes(if_node):
            match node:
                case ast.Import() | ast.ImportFrom():
                    for alias in node.names:
                        # Fixme: module
                        module = '' if isinstance(node, ast.Import) else node.module
                        _ = TypeCheckingImport(module, alias.name, alias.asname)  # ty: ignore[invalid-argument-type]
                        self._type_checking_imports[_.as_or_name] = _
                        console.line(f"  import [blue]{_.as_or_name} @{node.lineno}")

####################################################################################################

def main():
    parser = argparse.ArgumentParser(
         prog='py-introspection',
         description='Python Module Introspection',
    )
    parser.add_argument('module_path')
    args = parser.parse_args()

    module_path = Path(args.module_path)
    module = Module(module_path)

####################################################################################################

if __name__ == '__main__':
    main()
