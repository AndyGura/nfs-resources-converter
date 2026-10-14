"""
Warnings and game compatibility checks of the opened file (`library.block_checks`).
"""

from typing import Any, Dict, List

from library.block_checks import check_compatibility, collect_target_games, collect_warnings
from library.changes_service import ChangesService
from library.read_blocks.misc.compatibility import GAMES, GAME_ALIASES


class ChecksAPI:
    def __init__(self, api):
        self.api = api
        # (file, data object id, revision) -> warnings: the GUI polls them, data changes only with a revision
        self._warnings_cache_key = None
        self._warnings_cache = []
        self._warnings_cache_change = None

    def _current_file(self):
        file_api = self.api.file_api
        if file_api.current_file_block is None or file_api.current_file_data is None:
            return None
        return file_api.current_file_name, file_api.current_file_block, file_api.current_file_data

    def get_warnings(self) -> List[Dict[str, str]]:
        """Warnings of the opened file: [{id, message}]"""
        current = self._current_file()
        if current is None:
            return []
        name, block, data = current
        revision = ChangesService.local_revision
        last_change = ChangesService.changes[revision - 1] if 0 < revision <= len(ChangesService.changes) else None
        # a change entry is a new object every time: the same revision after undo + another edit is another key
        key = (name, id(data), revision, id(last_change))
        if key != self._warnings_cache_key:
            self._warnings_cache = collect_warnings(block, data, name)
            self._warnings_cache_key = key
            # keeps the change entry alive, so its id is not reused
            self._warnings_cache_change = last_change
        return self._warnings_cache

    def get_compatibility_games(self) -> List[Dict[str, str]]:
        """Games the opened file is made for, the ones its compatibility is checked with: [{alias, title}]"""
        current = self._current_file()
        if current is None:
            return []
        name, block, data = current
        targets = collect_target_games(block, data, name)
        return [{'alias': alias, 'title': title} for alias, title in GAMES if alias in targets]

    def check_compatibility(self, game: str) -> Dict[str, Any]:
        """Compatibility of the opened file with a game: {game, state, results: [{id, state, message}]}"""
        if game not in GAME_ALIASES:
            raise ValueError(f'Unknown game: {game}')
        current = self._current_file()
        if current is None:
            return {'game': game, 'state': 'unknown', 'results': []}
        name, block, data = current
        return check_compatibility(block, data, name, game)
