from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from libcst.codemod import CodemodTest
from libcst.codemod._context import CodemodContext
from libcst.metadata.full_repo_manager import FullRepoManager
from libcst.metadata.name_provider import FullyQualifiedNameProvider

from move_symbol.visitors import RemoveSymbolsVisitor


@contextmanager
def test_context():
    with TemporaryDirectory() as temp_dir:
        filename = "a/b.py"
        (Path(temp_dir) / "a").mkdir()
        (Path(temp_dir) / filename).touch()

        manager = FullRepoManager(temp_dir, [filename], [FullyQualifiedNameProvider])
        context = CodemodContext(
            filename=filename, full_module_name="a.b", metadata_manager=manager
        )
        yield context


class TestRemoveSymbolsVisitor(CodemodTest):
    TRANSFORM = RemoveSymbolsVisitor

    def test_noops(self):
        before = """
            def foo(): pass
            class Bar: pass
            baz = 1
        """
        after = """
            def foo(): pass
            class Bar: pass
            baz = 1
        """
        with test_context() as context:
            self.assertCodemod(before, after, {}, context_override=context)

    def test_remove_constant(self):
        before = """
            baz = 1
        """
        after = """
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"baz"}, context_override=context)

    def test_keep_nested_constant(self):
        before = """
            if True:
                baz = 1
        """
        after = """
            if True:
                baz = 1
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"baz"}, context_override=context)

    def test_remove_function(self):
        before = """
            def foo(): pass
        """
        after = """
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"foo"}, context_override=context)

    def test_keep_nested_function(self):
        before = """
            def foo2():
                def foo(): pass
        """
        after = """
            def foo2():
                def foo(): pass
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"foo"}, context_override=context)

    def test_remove_class(self):
        before = """
            class Bar: pass
        """
        after = """
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"Bar"}, context_override=context)

    def test_keep_nested_class(self):
        before = """
            class Bar2:
                class Bar: pass
        """
        after = """
            class Bar2:
                class Bar: pass
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"Bar"}, context_override=context)

    def test_remove_unused_import(self):
        before = """
            from x.y import z
            from a.b import c

            z
            class Bar:
                c
        """
        after = """
            from x.y import z

            z
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"Bar"}, context_override=context)
            self.assertEqual(
                context.scratch[self.TRANSFORM.CONTEXT_KEY]["imports"],
                {
                    "a.b.c",
                },
            )

    def test_remove_unused_import_include_implicit_siblings(self):
        before = """
            def foo():
                pass
            def bar():
                foo()
        """
        after = """
            def foo():
                pass
        """
        with test_context() as context:
            self.assertCodemod(before, after, {"bar"}, context_override=context)
            self.assertEqual(
                context.scratch[self.TRANSFORM.CONTEXT_KEY]["imports"], {"a.b.foo"}
            )