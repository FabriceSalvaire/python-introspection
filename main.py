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
# import ast
import importlib.util
import inspect
import sys
import types
import typing
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import cast

from rich import print
from rich.console import Console

# https://github.com/t3rn0/ast-comments
import ast_comments as ast

####################################################################################################

console = Console()

####################################################################################################

def load_module_from_path(path: Path) -> ModuleType:
    module_name = path.name
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

class VariableModuleAttribute:
    pass

####################################################################################################

class FunctionModuleAttribute(ModuleAttribute):

    ##############################################

    def __init__(self, module: Module, function: types.FunctionType) -> None:
        self.module = module
        self.function = function

        # See https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING
        # If you occasionally need to examine type annotations at runtime which may contain undefined
        # symbols, use annotationlib.get_annotations() with a format parameter of
        # annotationlib.Format.STRING or annotationlib.Format.FORWARDREF to safely retrieve the annotations
        # without raising NameError.

        print()
        print("[blue]Function signature:")
        signature = inspect.signature(
            function,
            # for TYPE_CHECKING: NameError: name 'Iterable' is not defined
            annotation_format=annotationlib.Format.STRING,
        )
        # str(signature) can return "(integers: 'Iterable[int]') -> 'None'"
        print(signature)
        for parameter in signature.parameters.values():
            # but here where is Iterable[int] ???
            print(f"- {parameter.kind} {parameter.name}: {parameter.annotation} = {parameter.default}")
            assert type(parameter.annotation) is str or inspect.Signature.empty
        return_type = signature.return_annotation
        assert type(return_type) is str or inspect.Signature.empty
        print(f"- return: {return_type}")

        # Retrun {} if any annotation !
        annotations = typing.get_type_hints(function, format=annotationlib.Format.STRING, include_extras=True)
        for name, type_ in annotations.items():
            assert type(type_) is str
            print(f"- annotation: {name} <{type_}>")
        # ! annotations = typing.get_type_hints(function, format=annotationlib.Format.VALUE, include_extras=True)
        annotations = typing.get_type_hints(function, format=annotationlib.Format.FORWARDREF, include_extras=True)
        for name, type_ in annotations.items():
            if isinstance(type_, annotationlib.ForwardRef):
                print(f"- [red]annotation[/]: {name} '{type_.__forward_arg__}' {type_}")
            else:
                print(f"- annotation: {name} <{type_}>   {type(type_)}")
                if hasattr(type_, '__origin__'):
                    print(f"    origin from dunder: {type_.__origin__}")
                    print(f"    args: {type_.__args__}")
                type_origin = typing.get_origin(type_)
                if type_origin is not None:
                    print(f"    origin from typing: {type_origin}")
                    try:
                        args = type_.get_args(type_)  # for typing.Annotated
                        print(f"    args: {args}")
                    except AttributeError:
                        pass

        print()
        print("[blue]Function docstring:")
        print(self.function.__doc__)
        # print(inspect.getdoc(self.function))

####################################################################################################

class ClassModuleAttribute:
    pass

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
        module = load_module_from_path(path)

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

        console.rule()
        print("[red]Module AST:")
        print(ast.dump(module_ast, indent=4))

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
                        print(f"match doc comment\n  {node}\n  {doc_comment}")
                        # Fixme: more than one target
                        target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                        match target:
                            case ast.Name():
                                print(target.id)
                            case _:
                                raise NotImplementedError

        console.rule()
        print("[red]module.__doc__")
        print(module.__doc__)

        console.rule()
        print("[red]Module Attributes:")
        print(f"Imported: {imported_name}")
        print(f"Type Checking Imported: {self._type_checking_imports.values()}")

        print(f"Defined: {modules_names}")
        for name in modules_names:
            console.rule()
            obj = getattr(module, name)
            print(f"{name} <{type(obj)}> {obj}")
            if inspect.isclass(obj):
                print("  is class")
                # print('doc', inspect.getdoc(obj))
                # print('comment', inspect.getcomments(obj))
                _lines, line_number = inspect.getsourcelines(obj)
                print(f"  @{line_number}")
                print(obj.__mro__[1:-1])
                print(obj.__doc__)
            elif inspect.isfunction(obj):
                function_module_attribute = FunctionModuleAttribute(self, obj)
            else:
                pass

    ##############################################

    def _on_type_checking(self, if_node: ast.If) -> None:
        for node in ast.iter_child_nodes(if_node):
            match node:
                case ast.Import():
                    for alias in node.names:
                        # Fixme: module
                        _ = TypeCheckingImport('', alias.name, alias.asname)
                        self._type_checking_imports[_.as_or_name] = _
                case ast.ImportFrom():
                    module = node.module
                    for alias in node.names:
                        _ = TypeCheckingImport(module, alias.name, alias.asname)  # ty: ignore[invalid-argument-type]
                        self._type_checking_imports[_.as_or_name] = _

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
