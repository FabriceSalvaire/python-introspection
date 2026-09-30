# https://docs.python.org/3/library/inspect.html

# for field, type_ in annotationlib.get_annotations(Foo).items():
#     print(f"field [blue]{field}[/] type [green]{type_}")
#     print(T.get_origin(type_))
#     print(T.get_args(type_))

# signature = inspect.signature(
#     obj,
#     # globals=globals,
#     globals=type_checking_globals,
#     locals=type_checking_globals,
# )

####################################################################################################

import annotationlib
import argparse
import importlib.util
import inspect
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
from rich import markup, print
from rich.console import Console

####################################################################################################

console = Console()

def E(obj: Any) -> str:
    return markup.escape(str(obj))

####################################################################################################

def dump_sys_modules() -> None:
    for name in sorted(sys.modules.keys()):
        module = sys.modules[name]
        print(f"{name} = {module}")

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
    except Exception:
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

class ModuleAttribute:

    ##############################################

    def __init__(self, module: Module) -> None:
        pass

####################################################################################################

class Variable:
    pass

####################################################################################################

class Function(ModuleAttribute):

    ##############################################

    def __init__(self, module: Module, function: types.FunctionType) -> None:
        self.module = module
        self.function = function

        # See https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING
        # If you occasionally need to examine type annotations at runtime which may contain undefined
        # symbols, use annotationlib.get_annotations() with a format parameter of
        # annotationlib.Format.STRING or annotationlib.Format.FORWARDREF to safely retrieve the annotations
        # without raising NameError.

        # print(f"{function.__annotations__}")
        # print(f"{function.__defaults__}")
        # print(f"{function.__kwdefaults__}")

        _lines, line_number = inspect.getsourcelines(function)
        print(f"Function [blue]{function.__name__}[/] @{line_number}")

        signature = inspect.signature(
            function,
            # for TYPE_CHECKING: NameError: name 'Iterable' is not defined
            annotation_format=annotationlib.Format.STRING,
        )
        # str(signature) can return "(integers: 'Iterable[int]') -> 'None'"
        print()
        print(f"[blue]Signature[/]: {function.__name__}{E(signature)}")
        for parameter in signature.parameters.values():
            # but here where is Iterable[int] ???
            print(f"  - {parameter.kind} [blue]{parameter.name}[/]: {E(parameter.annotation)} = {E(parameter.default)}")
            assert type(parameter.annotation) is str or inspect.Signature.empty
        return_type = signature.return_annotation
        assert type(return_type) is str or inspect.Signature.empty
        print(f"  - [blue]return[/]: {E(return_type)}")

        # Retrun {} if any annotation !
        print("annotation strings")
        annotations = typing.get_type_hints(function, format=annotationlib.Format.STRING, include_extras=True)
        for name, type_ in annotations.items():
            assert type(type_) is str
            print(f"  - [blue]{name}[/]: {E(type_)}")

        # This code can raise...
        # ! annotations = typing.get_type_hints(function, format=annotationlib.Format.VALUE, include_extras=True)

        print("annotations")
        annotations = typing.get_type_hints(function, format=annotationlib.Format.FORWARDREF, include_extras=True)
        for name, type_ in annotations.items():
            if isinstance(type_, annotationlib.ForwardRef):
                print(f"  - [red]{name}[/] ForwardRef '{type_.__forward_arg__}' {type_.__extra_names__}")
                print(E(forward_ref_arg(type_)))
                print(E(fix_forward_ref(type_)))
                # ! print(type_.__dict__)
                # for _ in dir(type_):
                #     print(_, getattr(type_, _))
            else:
                print(f"  - [blue]{name}[/] {E(type_)}")
                if hasattr(type_, '__origin__'):
                    print(f"      origin from dunder: {E(type_.__origin__)}")
                    print(f"      args: {E(type_.__args__)}")
                type_origin = typing.get_origin(type_)
                if type_origin is not None:
                    print(f"      origin from typing: {E(type_origin)}")
                    args = typing.get_args(type_)
                    print(f"      args: {E(args)}")

        print()
        print("[blue]Function docstring:")
        print(self.function.__doc__)
        # print(inspect.getdoc(self.function))

####################################################################################################

class Class:
    ##############################################

    def __init__(self, module: Module, klass: type) -> None:
        self.klass = klass

        _lines, line_number = inspect.getsourcelines(klass)
        print(f"  @{line_number}")

        # print("  is class")
        # # print('doc', inspect.getdoc(obj))
        # # print('comment', inspect.getcomments(obj))
        # _lines, line_number = inspect.getsourcelines(obj)
        # print(f"  @{line_number}")
        # print(obj.__mro__[1:-1])
        # print(obj.__doc__)

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
        print(f"[red]Load module [blue]{module_name}[/] from [green]{path}")
        module = load_module_from_path(path, module_name)

        # console.rule()
        # print(module.__dict__)
        # console.rule()
        # print(inspect.getmembers(module))
        # console.rule()
        # print(dir(module))

        # Get the module attibutes
        modules_names = set(dir(module)) - self.SPECIAL_NAMES

        # Build the AST for the module
        source = path.read_text()
        module_ast = ast.parse(source, type_comments=True)

        print()
        print("[red]Module AST:")
        console.rule()
        print(ast.dump(module_ast, indent=4))
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
        print()
        console.rule()
        print("[red]Doc Comments:")
        doc_comments = {}
        for node in ast.walk(module_ast):
            match node:
                case ast.Comment():
                    if node.value.startswith('#:'):
                        lineno = node.lineno  # ty: ignore[unresolved-attribute]
                        if not node.inline:
                            lineno += 1
                        print(f"  {node} @{lineno}")
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
                        print()
                        print(f"match doc comment for [blue]{target.id}[/]\n  {doc_comment}")
                        # Fixme: more than one target
        console.rule()

        print()
        console.rule()
        print("[red]module.__doc__")
        if module.__doc__:
            print(module.__doc__.strip())
        console.rule()

        print()
        console.rule()
        print("[red]Module Attributes:")
        print(f"Imported: {sorted(imported_name)}")
        print(f"Type Checking Imported: {self._type_checking_imports.values()}")
        print(f"Defined: {sorted(modules_names)}")

        for name in sorted(modules_names):
            print()
            console.rule()
            obj = getattr(module, name)
            if inspect.isclass(obj):
                klass = Class(self, obj)
            elif inspect.isfunction(obj):
                function = Function(self, obj)
            else:
                print(f"{name}: {type(obj)} = {obj}")

    ##############################################

    def _on_type_checking(self, if_node: ast.If) -> None:
        print()
        print(f"[red]Found if TYPE_CHECKING[/] @{if_node.lineno}")
        for node in ast.iter_child_nodes(if_node):
            match node:
                case ast.Import() | ast.ImportFrom():
                    for alias in node.names:
                        # Fixme: module
                        module = '' if isinstance(node, ast.Import) else node.module
                        _ = TypeCheckingImport(module, alias.name, alias.asname)
                        self._type_checking_imports[_.as_or_name] = _
                        print(f"  import [blue]{_.as_or_name} @{node.lineno}")

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
