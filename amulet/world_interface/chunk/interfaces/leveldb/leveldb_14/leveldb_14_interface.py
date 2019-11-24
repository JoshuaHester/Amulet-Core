from __future__ import annotations

from amulet.world_interface.chunk.interfaces.leveldb.leveldb_13.leveldb_13_interface import (
    LevelDB13Interface,
)


class LevelDB14Interface(LevelDB13Interface):
    def __init__(self):
        LevelDB13Interface.__init__(self)

        self.features["chunk_version"] = 14

    @staticmethod
    def is_valid(key):
        if key[0] != "leveldb":
            return False
        if key[1] != 14:
            return False
        return True


INTERFACE_CLASS = LevelDB14Interface