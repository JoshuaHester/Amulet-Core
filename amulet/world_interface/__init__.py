from __future__ import annotations

from amulet.world_interface import formats
from amulet.api.world import World
from amulet.api.errors import FormatLoaderInvalidFormat, FormatLoaderMismatched


def load_world(directory: str, _format: str = None, forced: bool = False) -> World:
    """
    Loads the world located at the given directory with the appropriate format loader.

    :param directory: The directory of the world
    :param _format: The format name to use
    :param forced: Whether to force load the world even if incompatible
    :return: The loaded world
    """
    if _format is not None:
        if _format not in formats.get_all_formats():
            raise FormatLoaderInvalidFormat(f"Could not find _format loader {_format}")
        if not forced and not formats.identify(directory) == _format:
            raise FormatLoaderMismatched(f"{_format} is incompatible")
    else:
        _format = formats.identify(directory)

    format_class = formats.get_format(_format)

    return World(directory, format_class(directory))


if __name__ == "__main__":
    import sys
    from amulet.api.block import Block
    import numpy

    w = load_world(sys.argv[1])
    c = w.get_chunk(0, 0)
    for block in c.blocks.ravel()[:4096:16]:    # the blockstates of one vertical column
        print(w.palette[block])
    stone = w.palette.get_add_block(Block(namespace='universal_minecraft', base_name='stone'))
    # blocks[0, 30, 0] = stone
    # c.blocks = numpy.full((16, 256, 16), stone)
    c.blocks = numpy.random.randint(0, len(w.palette.blocks()), size=(16, 256, 16))
    w.save()
    w.exit()

    w = load_world(sys.argv[1])
    c = w.get_chunk(0, 0)
    for block in c.blocks.ravel()[:4096:16]:  # the blockstates of one vertical column
        print(w.palette[block])
