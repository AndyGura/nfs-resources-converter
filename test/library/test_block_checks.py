import unittest

from library.block_checks import check_compatibility, collect_warnings
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
            return (
                Compatibility.not_compatible(f'value {data["value"]}') if data['value'] > 1 else Compatibility.unknown()
            )
        return super().get_compatibility(data, game, ctx)


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
        self.assertEqual(res['state'], Compatibility.COMPATIBLE)
        self.assertEqual(len(res['results']), 5)

    def test_not_compatible_wins(self):
        res = check_compatibility(RootBlock(), _data(values=(1, 1, 1), delegated=3, optional=0), 'FILE.BIN', 'nfs2')
        self.assertEqual(res['state'], Compatibility.NOT_COMPATIBLE)
        # unknown results without a message are left out
        self.assertEqual(
            res['results'], [{'id': 'FILE.BIN__delegated/data', 'state': 'not_compatible', 'message': 'value 3'}]
        )

    def test_unknown_by_default(self):
        res = check_compatibility(RootBlock(), _data(), 'FILE.BIN', 'nfs6')
        self.assertEqual(res, {'game': 'nfs6', 'state': 'unknown', 'results': []})

    def test_not_compatible_needs_message(self):
        with self.assertRaises(ValueError):
            Compatibility.not_compatible('')
