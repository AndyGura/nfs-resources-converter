import unittest

from library.block_checks import check_compatibility, collect_target_games, collect_warnings
from library.lazy import LazyDict, MemorySource, Slot, is_loaded
from library.read_blocks import (
    ArrayBlock,
    DeclarativeCompoundBlock,
    DelegateBlock,
    IntegerBlock,
    OptionalBlock,
)
from library.read_blocks.misc.compatibility import Compatibility


class WarnedBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        value = IntegerBlock(length=1)

    def get_warnings(self, data, ctx):
        # the context has the block's own data
        assert ctx.data('value') == data['value']
        return [f'value {data["value"]} > 2'] if data['value'] > 2 else []

    def get_compatibility(self, data, game, ctx):
        if game == 'tnfs':
            return Compatibility.compatible()
        if game == 'nfs2':
            if data['value'] > 2:
                return Compatibility.not_compatible(f'value {data["value"]}', 'value above 2')
            return (
                Compatibility.not_compatible(f'value {data["value"]}') if data['value'] > 1 else Compatibility.unknown()
            )
        return super().get_compatibility(data, game, ctx)


class TargetedBlock(IntegerBlock):
    def get_target_games(self, data, ctx):
        return ['nfs3', 'nfs2', 'tnfs'] if data else ['nfs2', 'nfs4']


class TargetsRootBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        a = TargetedBlock(length=1)
        b = ArrayBlock(length=2, child=TargetedBlock(length=1))


class RootBlock(DeclarativeCompoundBlock):
    class Fields(DeclarativeCompoundBlock.Fields):
        items = ArrayBlock(length=3, child=WarnedBlock())
        delegated = DelegateBlock(possible_blocks=[IntegerBlock(length=1), WarnedBlock()], choice_index=1)
        optional = OptionalBlock(child=WarnedBlock(), criteria=lambda ctx: True)
        plain = ArrayBlock(length=2, child=IntegerBlock(length=1))


class BrokenBlock(IntegerBlock):
    def get_warnings(self, data, ctx):
        raise ValueError('boom')


def _data(values=(1, 2, 2), delegated=7, optional=0):
    return {
        'items': [{'value': v} for v in values],
        'delegated': {'choice_index': 1, 'data': {'value': delegated}},
        'optional': {'value': optional},
        'plain': [1, 2],
    }


class TestCollectWarnings(unittest.TestCase):
    def test_warnings_with_ids(self):
        res = collect_warnings(RootBlock(), _data(values=(1, 5, 2), optional=3), 'FILE.BIN')
        self.assertEqual(
            res,
            [
                {'id': 'FILE.BIN__items/1', 'message': 'value 5 > 2'},
                {'id': 'FILE.BIN__delegated/data', 'message': 'value 7 > 2'},
                # an optional field has the id of its child
                {'id': 'FILE.BIN__optional', 'message': 'value 3 > 2'},
            ],
        )

    def test_no_warnings(self):
        self.assertEqual(collect_warnings(RootBlock(), _data(delegated=0), 'FILE.BIN'), [])

    def test_blocks_without_checks_are_skipped(self):
        # leaf arrays with no checks below are not walked: data of a wrong type doesn't matter there
        data = _data(delegated=0)
        data['plain'] = object()
        self.assertEqual(collect_warnings(RootBlock(), data, 'FILE.BIN'), [])

    def test_failing_check_becomes_a_warning(self):
        res = collect_warnings(BrokenBlock(length=1), 1, 'FILE.BIN')
        self.assertEqual(res, [{'id': 'FILE.BIN', 'message': 'Could not check this block: ValueError: boom'}])


class TestCheckCompatibility(unittest.TestCase):
    def test_compatible(self):
        res = check_compatibility(RootBlock(), _data(), 'FILE.BIN', 'tnfs')
        self.assertEqual(res, {'game': 'tnfs', 'state': Compatibility.COMPATIBLE, 'problems': []})

    def test_not_compatible_wins(self):
        res = check_compatibility(RootBlock(), _data(values=(1, 2, 1), delegated=3, optional=0), 'FILE.BIN', 'nfs2')
        self.assertEqual(res['state'], Compatibility.NOT_COMPATIBLE)
        # every problem of every block, in tree order
        self.assertEqual(
            res['problems'],
            [
                {'id': 'FILE.BIN__items/1', 'message': 'value 2'},
                {'id': 'FILE.BIN__delegated/data', 'message': 'value 3'},
                {'id': 'FILE.BIN__delegated/data', 'message': 'value above 2'},
            ],
        )

    def test_unknown_by_default(self):
        res = check_compatibility(RootBlock(), _data(), 'FILE.BIN', 'nfs6')
        self.assertEqual(res, {'game': 'nfs6', 'state': 'unknown', 'problems': []})

    def test_not_compatible_needs_reasons(self):
        with self.assertRaises(ValueError):
            Compatibility.not_compatible()
        with self.assertRaises(ValueError):
            Compatibility.not_compatible('reason', '')


class TestCollectTargetGames(unittest.TestCase):
    def test_games_every_block_agrees_on(self):
        block = TargetsRootBlock()
        # in GAMES order
        self.assertEqual(collect_target_games(block, {'a': 1, 'b': [1, 1]}, 'F'), ['tnfs', 'nfs2', 'nfs3'])
        self.assertEqual(collect_target_games(block, {'a': 1, 'b': [1, 0]}, 'F'), ['nfs2'])

    def test_no_opinion(self):
        self.assertEqual(collect_target_games(RootBlock(), _data(), 'F'), [])


class _FakeParentCtx:
    def detached(self, buffer):
        return None


def _lazy_item(value):
    return LazyDict(Slot(MemorySource(b''), 0, 0, lambda ctx, slot: {'value': value}, _FakeParentCtx()))


class TestLazyParts(unittest.TestCase):
    def test_warnings_skip_unloaded_parts(self):
        data = _data(values=(1, 2, 2))
        data['items'][1] = _lazy_item(5)
        self.assertEqual(
            collect_warnings(RootBlock(), data, 'F.BIN'), [{'id': 'F.BIN__delegated/data', 'message': 'value 7 > 2'}]
        )
        self.assertFalse(is_loaded(data['items'][1]))
        data['items'][1].load()
        self.assertIn({'id': 'F.BIN__items/1', 'message': 'value 5 > 2'}, collect_warnings(RootBlock(), data, 'F.BIN'))

    def test_compatibility_loads_parts_for_the_check(self):
        data = _data(values=(1, 1, 1), delegated=1)
        data['items'][1] = _lazy_item(5)
        report = check_compatibility(RootBlock(), data, 'F.BIN', 'nfs2')
        self.assertEqual(report['state'], Compatibility.NOT_COMPATIBLE)
        self.assertEqual([p['id'] for p in report['problems']], ['F.BIN__items/1', 'F.BIN__items/1'])
        # unloaded again after the check
        self.assertFalse(is_loaded(data['items'][1]))
