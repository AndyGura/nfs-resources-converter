from typing import Optional

# Games of the compatibility check, as (alias, title), in release order. A block's `get_compatibility` receives the
# alias.
GAMES = [
    ('tnfs', 'The Need For Speed (DOS, SE)'),
    ('tnfs_3do', 'The Need For Speed (3DO)'),
    ('nfs2', 'Need For Speed II'),
    ('nfs2_se', 'Need For Speed II SE'),
    ('nfs3', 'Need For Speed III: Hot Pursuit'),
    ('nfs4', 'Need For Speed: High Stakes'),
    ('nfs5', 'Need For Speed: Porsche Unleashed'),
    ('nfs6', 'Need For Speed: Hot Pursuit 2'),
    ('nfsu', 'Need For Speed: Underground'),
    ('nfsu2', 'Need For Speed: Underground 2'),
    ('nfsmw', 'Need For Speed: Most Wanted (2005)'),
]

GAME_ALIASES = [alias for alias, _ in GAMES]


class Compatibility:
    """Result of `DataBlock.get_compatibility`: whether a game can use the block's data as it is now"""

    COMPATIBLE = 'compatible'
    NOT_COMPATIBLE = 'not_compatible'
    UNKNOWN = 'unknown'

    def __init__(self, state: str, message: Optional[str] = None):
        if state not in (self.COMPATIBLE, self.NOT_COMPATIBLE, self.UNKNOWN):
            raise ValueError(f'Unknown compatibility state: {state}')
        if state == self.NOT_COMPATIBLE and not message:
            raise ValueError('A non-compatible result needs a message')
        self.state = state
        self.message = message

    @classmethod
    def compatible(cls, message: str = None) -> 'Compatibility':
        return cls(cls.COMPATIBLE, message)

    @classmethod
    def not_compatible(cls, message: str) -> 'Compatibility':
        return cls(cls.NOT_COMPATIBLE, message)

    @classmethod
    def unknown(cls, message: str = None) -> 'Compatibility':
        return cls(cls.UNKNOWN, message)

    def __eq__(self, other):
        return isinstance(other, Compatibility) and (self.state, self.message) == (other.state, other.message)

    def __repr__(self):
        return f'Compatibility({self.state!r}, {self.message!r})'
