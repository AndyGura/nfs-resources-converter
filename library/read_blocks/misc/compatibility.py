from typing import List, Sequence

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
    """
    Result of `DataBlock.get_compatibility`: whether a game can use the block's data as it is now. A non-compatible
    result lists its problems, the reason of each, one text per problem; the other states have no text
    """

    COMPATIBLE = 'compatible'
    NOT_COMPATIBLE = 'not_compatible'
    UNKNOWN = 'unknown'

    def __init__(self, state: str, problems: Sequence[str] = ()):
        if state not in (self.COMPATIBLE, self.NOT_COMPATIBLE, self.UNKNOWN):
            raise ValueError(f'Unknown compatibility state: {state}')
        problems = list(problems)
        if state == self.NOT_COMPATIBLE and (not problems or not all(problems)):
            raise ValueError('A non-compatible result needs the reason of every problem')
        if state != self.NOT_COMPATIBLE and problems:
            raise ValueError('Only a non-compatible result has problems')
        self.state = state
        self.problems: List[str] = problems

    @classmethod
    def compatible(cls) -> 'Compatibility':
        return cls(cls.COMPATIBLE)

    @classmethod
    def not_compatible(cls, *problems: str) -> 'Compatibility':
        return cls(cls.NOT_COMPATIBLE, problems)

    @classmethod
    def unknown(cls) -> 'Compatibility':
        return cls(cls.UNKNOWN)

    def __eq__(self, other):
        return isinstance(other, Compatibility) and (self.state, self.problems) == (other.state, other.problems)

    def __repr__(self):
        return f'Compatibility({self.state!r}, {self.problems!r})'
