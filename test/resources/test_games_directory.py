import hashlib
import os
import re
import subprocess
import sys
import time
import unittest
from collections import defaultdict
from io import BytesIO
from multiprocessing import Pool, cpu_count
from typing import List, Any, Dict, Tuple, Optional

# Huge (more than 10 minutes): opt in with NFS_GAMES_ROUNDTRIP=1. NFS_GAMES_DIR points it at another directory
# (e.g. test/samples for a quick smoke run), NFS_GAMES_EXTENSIONS=.FSH,.QFS limits it to some file extensions
GAMES_DIR = os.environ.get(
    'NFS_GAMES_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'games')
)
EXCLUDED_EXTENSIONS = {
    '.EXE',
    '.DLL',
    '.INF',
    '.INV',
    '.PIF',
    '.TXT',
    '.CFG',
    '.ICO',
    '.ID0',
    '.ID1',
    '.ID2',
    '.NAM',
    '.TIL',
    '.ENG',
    '.GER',
    '.ION',
    '.UC',
    '.UV',
    '.0',
    '.O',
}
STATS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_files_stats.txt')
FAILURES_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_files_failures.txt')
REGRESSIONS_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_files_regressions.txt')

# outcomes of a single file, ordered by how far it got
UNSUPPORTED = 'unsupported'
READ_FAILED = 'read_failed'
WRITE_FAILED = 'write_failed'
READ_AGAIN_FAILED = 'read_again_failed'
DIFFERENT = 'different'
IDENTICAL = 'identical'
OUTCOMES_AFTER_READ = [WRITE_FAILED, READ_AGAIN_FAILED, DIFFERENT, IDENTICAL]
OUTCOMES_AFTER_WRITE = [READ_AGAIN_FAILED, DIFFERENT, IDENTICAL]
OUTCOMES_AFTER_READ_AGAIN = [DIFFERENT, IDENTICAL]


def deep_equal(a: Any, b: Any) -> bool:
    """
    Perform a deep equality comparison between two objects.

    Args:
        a: First object to compare
        b: Second object to compare

    Returns:
        True if objects are deeply equal, False otherwise
    """
    # Check if objects are of the same type
    if type(a) != type(b):
        return False

    # Handle None
    if a is None:
        return b is None

    # Handle basic types
    if isinstance(a, (int, float, str, bool)):
        return a == b

    # Handle lists
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(deep_equal(a[i], b[i]) for i in range(len(a)))

    # Handle dictionaries
    if isinstance(a, dict):
        if len(a) != len(b):
            return False
        if set(a.keys()) != set(b.keys()):
            return False
        return all(deep_equal(a[k], b[k]) for k in a.keys())

    # Handle tuples
    if isinstance(a, tuple):
        if len(a) != len(b):
            return False
        return all(deep_equal(a[i], b[i]) for i in range(len(a)))

    # Handle sets
    if isinstance(a, set):
        return a == b

    # For other types, use equality operator
    return a == b


def file_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].upper() or '(no extension)'


# Our compressor never produces the same bytes as EA's one, so a compressed block can't be compared to the original
# one byte by byte. Instead, in worker processes, every uncompress call remembers the original compressed bytes by
# hash of the uncompressed result, and every compress call:
#  1. uncompresses what our compressor produced and checks it gives back the input (catches compressor bugs);
#  2. if the input equals some original uncompressed content, returns the original compressed bytes, so the rest of the
#     file (e.g. a BIGF archive around a compressed item) is still compared byte by byte. Otherwise the uncompressed
#     content differs from the original one: returns our compressed bytes, the file won't be identical.
_original_compressed = {}
_compression_stats = None


def _reset_compression_tracking():
    global _compression_stats
    _original_compressed.clear()
    _compression_stats = {'blocks': 0, 'compressor_failures': [], 'content_mismatches': 0}


def _install_compression_tracking():
    from resources.eac.compressions.huff import HuffCompression
    from resources.eac.compressions.jdlz import JdlzCompression
    from resources.eac.compressions.qfs2 import Qfs2Compression
    from resources.eac.compressions.qfs3 import Qfs3Compression
    from resources.eac.compressions.ref_pack import RefPackCompression

    original_uncompress = {}
    for cls in [RefPackCompression, Qfs2Compression, Qfs3Compression, JdlzCompression, HuffCompression]:
        original_uncompress[cls] = cls.uncompress

        def uncompress(self, buffer, input_length, _original=cls.uncompress):
            start = buffer.tell()
            compressed = buffer.read(input_length) if input_length is not None else buffer.read()
            buffer.seek(start)
            uncompressed = _original(self, buffer, input_length)
            _original_compressed[hashlib.sha1(bytes(uncompressed)).digest()] = compressed
            return uncompressed

        cls.uncompress = uncompress

    for cls in [Qfs2Compression, JdlzCompression]:

        def compress(self, buffer, input_length, *args, _original=cls.compress, _cls=cls, **kwargs):
            start = buffer.tell()
            uncompressed = bytes(buffer.read(input_length))
            buffer.seek(start)
            compressed = _original(self, buffer, input_length, *args, **kwargs)
            _compression_stats['blocks'] += 1
            try:
                compressed_bytes = bytes(compressed)
                uncompressed_again = original_uncompress[_cls](_cls(), BytesIO(compressed_bytes), len(compressed_bytes))
                if bytes(uncompressed_again) != uncompressed:
                    _compression_stats['compressor_failures'].append(
                        f'{_cls.__name__}: uncompressed {len(uncompressed_again)} bytes differ from '
                        f'{len(uncompressed)} input bytes'
                    )
            except Exception as ex:
                _compression_stats['compressor_failures'].append(
                    f'{_cls.__name__}: failed to uncompress own output: {type(ex).__name__}: {ex}'
                )
            original = _original_compressed.get(hashlib.sha1(uncompressed).digest())
            if original is None:
                _compression_stats['content_mismatches'] += 1
                return compressed
            return original

        cls.compress = compress


def _init_worker():
    import logging

    # compressors print their progress, results are printed by the main process
    sys.stdout = open(os.devnull, 'w')
    logging.disable(logging.CRITICAL)
    _install_compression_tracking()


def _clear_caches():
    from library.loader import files_cache
    from library.read_blocks import DataBlock

    # every file is read once, keeping them all in memory only bloats worker processes
    files_cache.clear()
    DataBlock.root_read_ctx.children.clear()


def _error_text(ex: Exception) -> str:
    return f'{type(ex).__name__}: {ex}'.replace('\n', ' ')


def check_file(file_path: str) -> Dict:
    """
    Reads the file, writes it back to bytes and compares the output with the original file. If they differ, reads the
    output again and compares parsed data with the original parsed data. Runs in a worker process
    """
    from library import require_file
    from library.context import ReadContext
    from library.loader import probe_block_class

    _clear_caches()
    _reset_compression_tracking()
    start_time = time.time()
    result = {'path': file_path, 'ext': file_extension(file_path), 'outcome': None, 'error': None}
    try:
        with open(file_path, 'rb') as f:
            original = f.read()
        try:
            probe_block_class(BytesIO(original), file_path, len(original))
        except NotImplementedError:
            result['outcome'] = UNSUPPORTED
            return result

        try:
            (name, block, data) = require_file(file_path)
        except Exception as ex:
            result['outcome'] = READ_FAILED
            result['error'] = _error_text(ex)
            return result

        try:
            output = bytes(block.pack(data, name=name))
        except Exception as ex:
            result['outcome'] = WRITE_FAILED
            result['error'] = _error_text(ex)
            return result

        if output == original:
            result['outcome'] = IDENTICAL
            return result

        try:
            read_again_data = block.unpack(
                ReadContext(buffer=BytesIO(output), read_bytes_amount=len(output)),
                name=name,
                read_bytes_amount=len(output),
            )
        except Exception as ex:
            result['outcome'] = READ_AGAIN_FAILED
            result['error'] = f'Failed to read written data: {_error_text(ex)}'
            return result
        if not deep_equal(data, read_again_data):
            result['outcome'] = READ_AGAIN_FAILED
            result['error'] = 'Read-again data differs from original data'
            return result

        result['outcome'] = DIFFERENT
        if len(output) != len(original):
            result['error'] = f'Output length ({len(output)}) differs from input length ({len(original)})'
        else:
            first_diff = next(i for i in range(len(output)) if output[i] != original[i])
            result['error'] = f'Output differs from input at offset 0x{first_diff:X}'
        if _compression_stats['content_mismatches']:
            result['error'] += (
                f'; uncompressed contents of {_compression_stats["content_mismatches"]} compressed block(s) differ'
            )
        return result
    except Exception as ex:
        result['outcome'] = READ_FAILED
        result['error'] = _error_text(ex)
        return result
    finally:
        result['compressed_blocks'] = _compression_stats['blocks']
        result['compressor_failures'] = _compression_stats['compressor_failures']
        result['duration'] = time.time() - start_time
        _clear_caches()


def _format_rate(count: int, total: int) -> str:
    return f'{(count / total) * 100:.2f}% ({count}/{total})'


class TestGamesDirectory(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('NFS_GAMES_ROUNDTRIP'), 'takes more than 10 minutes, set NFS_GAMES_ROUNDTRIP=1')
    def test_all_game_files_should_remain_the_same(self):
        """
        Test that goes through the entire ./games/ directory, reads each file, writes it back to a bytes object,
        and compares the output with the input. Files are processed by (cpu count / 2) worker processes. Compressed
        blocks are compared by their uncompressed contents, our compressor output is checked by uncompressing it.
        Writes statistics to game_files_stats.txt and all failures after a successful read to game_files_failures.txt.
        Fails if any extension has fewer passed files than in the committed game_files_stats.txt, regressed extensions
        are written to game_files_regressions.txt
        """
        start_time = time.time()

        GREEN = '\033[32m'
        RED = '\033[31m'
        YELLOW = '\033[33m'
        RESET = '\033[0m'

        all_files = [x for x in self._get_all_files(GAMES_DIR) if file_extension(x) not in EXCLUDED_EXTENSIONS]
        only_extensions = os.environ.get('NFS_GAMES_EXTENSIONS')
        if only_extensions:
            only_extensions = {x.strip().upper() for x in only_extensions.split(',')}
            all_files = [x for x in all_files if file_extension(x) in only_extensions]
        # the biggest files go first, so that the last running ones are fast
        all_files.sort(key=lambda x: (-os.path.getsize(x), x))
        total_files = len(all_files)

        processes = max(1, cpu_count() // 2)
        print(f'Checking {total_files} files in {os.path.abspath(GAMES_DIR)} using {processes} processes')
        results = []
        with Pool(processes=processes, initializer=_init_worker) as pool:
            for result in pool.imap_unordered(check_file, all_files, chunksize=1):
                results.append(result)
                outcome = result['outcome']
                if outcome == IDENTICAL:
                    marks = f'{GREEN}✓✓✓✓{RESET}'
                elif outcome == UNSUPPORTED:
                    marks = f'{YELLOW}-{RESET}'
                else:
                    passed = {READ_FAILED: 0, WRITE_FAILED: 1, READ_AGAIN_FAILED: 2, DIFFERENT: 3}[outcome]
                    marks = '✓' * passed + f'{RED}❌ ({result["error"]}){RESET}'
                if result['compressor_failures']:
                    marks += f' {RED}compressor: {"; ".join(result["compressor_failures"])}{RESET}'
                print(f'{len(results)} / {total_files} {result["path"]} {marks} {result["duration"]:.1f}s', flush=True)

        elapsed_time = time.time() - start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_spent = f'Total time: {int(hours):02}:{int(minutes):02}:{seconds:.2f}'

        extension_rates = self._extension_rates(results)
        report = self._build_report(results, total_files, extension_rates) + ['', '--- Time Spent ---', time_spent]
        print('\n' + '\n'.join(report))
        if 'NFS_GAMES_DIR' in os.environ:
            # other files, nothing to compare with
            return

        # the committed stats are the baseline: any extension, which got fewer passed files in any section, regressed
        regressions = self._find_regressions(self._read_committed_rates(), extension_rates)
        regressions_report = self._build_regressions_report(regressions)
        print('\n' + '\n'.join(regressions_report))
        if not only_extensions:
            # a partial run leaves committed reports as they are
            with open(STATS_FILE_PATH, 'w') as stats_file:
                stats_file.write('\n'.join(report) + '\n')
            with open(FAILURES_FILE_PATH, 'w') as failures_file:
                failures_file.write('\n'.join(self._build_failures_report(results)) + '\n')
            with open(REGRESSIONS_FILE_PATH, 'w') as regressions_file:
                regressions_file.write('\n'.join(regressions_report) + '\n')
            print(f'\nStatistics exported to: {STATS_FILE_PATH}')
            print(f'Failures exported to: {FAILURES_FILE_PATH}')
            print(f'Regressions exported to: {REGRESSIONS_FILE_PATH}')
        if regressions:
            self.fail(
                f'{len(regressions)} extension rate(s) regressed compared to committed stats: '
                + ', '.join(sorted({ext for _, ext, _, _ in regressions}))
            )

    def _extension_rates(self, results: List[Dict]) -> Dict[str, Dict[str, Tuple[int, int]]]:
        """{section title: {extension: (passed files, total files)}}"""
        by_extension = defaultdict(list)
        compressed_by_extension = defaultdict(list)
        for result in results:
            by_extension[result['ext']].append(result)
            if result['compressed_blocks'] > 0:
                compressed_by_extension[result['ext']].append(result)

        def rates(outcomes):
            return {
                ext: (len([x for x in items if x['outcome'] in outcomes]), len(items))
                for ext, items in by_extension.items()
            }

        return {
            'Read Success Rates (Test 1)': rates(OUTCOMES_AFTER_READ),
            'Write Success Rates (Test 2)': rates(OUTCOMES_AFTER_WRITE),
            'Read-Again Success Rates (Test 3)': rates(OUTCOMES_AFTER_READ_AGAIN),
            'Comparison Success Rates (Test 4)': rates([IDENTICAL]),
            'Compressor Round-Trip Success Rates': {
                ext: (len([x for x in items if not x['compressor_failures']]), len(items))
                for ext, items in compressed_by_extension.items()
            },
        }

    def _build_report(
        self, results: List[Dict], total_files: int, extension_rates: Dict[str, Dict[str, Tuple[int, int]]]
    ) -> List[str]:
        def count(outcomes):
            return len([x for x in results if x['outcome'] in outcomes])

        compressed = [x for x in results if x['compressed_blocks'] > 0]
        report = [
            '--- Test Statistics ---',
            f'Total files tested: {total_files}',
            f'Files without parser: {count([UNSUPPORTED])}',
            f'Files read successfully: {count(OUTCOMES_AFTER_READ)}',
            f'Files written successfully: {count(OUTCOMES_AFTER_WRITE)}',
            f'Files read again successfully: {count(OUTCOMES_AFTER_READ_AGAIN)}',
            f'Files passed comparison test: {count([IDENTICAL])}',
            f'Files with compressed blocks written: {len(compressed)}',
            f'Files with compressor round-trip failures: {len([x for x in compressed if x["compressor_failures"]])}',
        ]
        # extensions without a single read file are formats we don't support, they'd be 0% in every section
        read_extensions = {ext for ext, (passed, _) in extension_rates['Read Success Rates (Test 1)'].items() if passed}
        for title, rates in extension_rates.items():
            report += ['', f'--- File Extension {title} ---']
            rates = [(ext, rate) for ext, rate in rates.items() if ext in read_extensions]
            # same rates are sorted by extension, so that the report is stable between runs
            for ext, (passed, total) in sorted(rates, key=lambda x: (-x[1][0] / x[1][1], x[0])):
                report.append(f'{ext}: {_format_rate(passed, total)}')
        return report

    def _read_committed_rates(self) -> Dict[str, Dict[str, Tuple[float, Optional[int], str]]]:
        """
        {section title: {extension: (rate in percents, passed files, rate as written)}} from the stats file in git HEAD,
        so that re-runs are compared with the same baseline until new stats are committed. Passed files are None for
        stats written without counts
        """
        try:
            stats = subprocess.run(
                ['git', 'show', f'HEAD:./{os.path.basename(STATS_FILE_PATH)}'],
                cwd=os.path.dirname(STATS_FILE_PATH),
                capture_output=True,
                check=True,
                text=True,
            ).stdout
        except OSError, subprocess.CalledProcessError:
            print('No committed stats to compare with')
            return {}
        committed_rates = defaultdict(dict)
        title = None
        for line in stats.splitlines():
            line = line.strip()
            section_match = re.match(r'^--- File Extension (.+) ---$', line)
            if section_match:
                title = section_match.group(1)
                continue
            rate_match = re.match(r'^(.+): ((\d+(?:\.\d+)?)%(?: \((\d+)/\d+\))?)$', line)
            if title and rate_match:
                ext, written, rate, passed = rate_match.groups()
                committed_rates[title][ext] = (float(rate), int(passed) if passed is not None else None, written)
            elif line.startswith('---'):
                title = None
        return committed_rates

    def _find_regressions(
        self,
        committed_rates: Dict[str, Dict[str, Tuple[float, Optional[int], str]]],
        extension_rates: Dict[str, Dict[str, Tuple[int, int]]],
    ) -> List[Tuple[str, str, str, Tuple[int, int]]]:
        """
        (section title, extension, committed rate as written, (passed, total)) of every extension with fewer passed
        files than committed. Fewer passed files, not a lower rate: new unsupported game files only lower the rate.
        Stats without counts are compared by rate. Extensions, which aren't in both, aren't compared
        """
        regressions = []
        for title, rates in extension_rates.items():
            for ext, (passed, total) in sorted(rates.items()):
                committed = committed_rates.get(title, {}).get(ext)
                if committed is None:
                    continue
                committed_rate, committed_passed, written = committed
                if committed_passed is not None:
                    regressed = passed < committed_passed
                else:
                    # compared as rounded in the report, so that float noise isn't a regression
                    regressed = round((passed / total) * 100, 2) < committed_rate
                if regressed:
                    regressions.append((title, ext, written, (passed, total)))
        return regressions

    def _build_regressions_report(self, regressions: List[Tuple[str, str, str, Tuple[int, int]]]) -> List[str]:
        report = [f'--- Regressed extensions: {len({ext for _, ext, _, _ in regressions})} ---']
        report += sorted({ext for _, ext, _, _ in regressions})
        for title in dict.fromkeys(title for title, _, _, _ in regressions):
            report += ['', f'--- File Extension {title} ---']
            for _, ext, committed, (passed, total) in [x for x in regressions if x[0] == title]:
                report.append(f'{ext}: {committed} -> {_format_rate(passed, total)}')
        return report

    def _build_failures_report(self, results: List[Dict]) -> List[str]:
        """Every file, which was read, but failed further, plus compressor failures. Sorted to be stable between runs"""
        games_dir = os.path.abspath(GAMES_DIR)
        report = []
        for title, outcome in [
            ('Write failures (Test 2)', WRITE_FAILED),
            ('Read-again failures (Test 3)', READ_AGAIN_FAILED),
            ('Comparison failures (Test 4)', DIFFERENT),
            ('Read failures (Test 1)', READ_FAILED),
        ]:
            failed = sorted(
                (os.path.relpath(x['path'], games_dir), x['error']) for x in results if x['outcome'] == outcome
            )
            report += [f'--- {title}: {len(failed)} ---'] + [f'{path}\t\t{error}' for path, error in failed] + ['']
        compressor_failed = sorted(
            (os.path.relpath(x['path'], games_dir), '; '.join(x['compressor_failures']))
            for x in results
            if x['compressor_failures']
        )
        report += [f'--- Compressor round-trip failures: {len(compressor_failed)} ---'] + [
            f'{path}\t\t{error}' for path, error in compressor_failed
        ]
        return report

    def _get_all_files(self, directory: str) -> List[str]:
        """
        Recursively get all files in a directory.

        Args:
            directory: The directory to search in.

        Returns:
            A list of file paths.
        """
        all_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                all_files.append(os.path.join(root, file))
        return all_files
