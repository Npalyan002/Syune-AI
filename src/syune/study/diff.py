"""Structural block comparison only; not retrieval or semantic matching."""
from difflib import SequenceMatcher

from .model import BlockChange, BlockChangeKind


def compare_blocks(previous: tuple[tuple[str, str], ...],
                   current: tuple[tuple[str, str], ...]) -> tuple[BlockChange, ...]:
    before = [fingerprint for _, fingerprint in previous]
    after = [fingerprint for _, fingerprint in current]
    matcher = SequenceMatcher(a=before, b=after, autojunk=False)
    changes: list[BlockChange] = []
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "equal":
            changes.extend(BlockChange(BlockChangeKind.UNCHANGED, previous[i][0], current[j][0])
                           for i, j in zip(range(a1, a2), range(b1, b2)))
        elif tag == "insert":
            changes.extend(BlockChange(BlockChangeKind.NEW, None, current[j][0])
                           for j in range(b1, b2))
        elif tag == "delete":
            changes.extend(BlockChange(BlockChangeKind.REMOVED, previous[i][0], None)
                           for i in range(a1, a2))
        else:
            paired = min(a2 - a1, b2 - b1)
            changes.extend(BlockChange(BlockChangeKind.CHANGED, previous[a1 + k][0], current[b1 + k][0])
                           for k in range(paired))
            changes.extend(BlockChange(BlockChangeKind.REMOVED, previous[i][0], None)
                           for i in range(a1 + paired, a2))
            changes.extend(BlockChange(BlockChangeKind.NEW, None, current[j][0])
                           for j in range(b1 + paired, b2))
    return tuple(changes)
