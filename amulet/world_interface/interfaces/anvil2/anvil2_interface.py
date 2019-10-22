from __future__ import annotations

from typing import List, Tuple

import numpy
import amulet_nbt as nbt

from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.world_interface.interfaces import Interface
from amulet.utils.world_utils import get_smallest_dtype
from amulet.world_interface import translators


def properties_to_string(props: dict) -> str:
    """
    Converts a dictionary of blockstate properties to a string

    :param props: The dictionary of blockstate properties
    :return: The string version of the supplied blockstate properties
    """
    result = []
    for key, value in props.items():
        result.append("{}={}".format(key, value))
    return ",".join(result)


def _decode_long_array(long_array: numpy.ndarray, size: int) -> numpy.ndarray:
    """
    Decode an long array (from BlockStates or Heightmaps)
    :param long_array: Encoded long array
    :size uint: The expected size of the returned array
    :return: Decoded array as numpy array
    """
    long_array = numpy.array(long_array, dtype=">q")
    bits_per_block = (len(long_array) * 64) // size
    binary_blocks = numpy.unpackbits(
        long_array[::-1].astype(">i8").view("uint8")
    ).reshape(-1, bits_per_block)
    return binary_blocks.dot(2 ** numpy.arange(binary_blocks.shape[1] - 1, -1, -1))[
        ::-1  # Undo the bit-shifting that Minecraft does with the palette indices
    ][:size]


def _encode_long_array(array: numpy.ndarray) -> numpy.ndarray:
    """
    Encode an long array (from BlockStates or Heightmaps)
    :param array: A numpy array of the data to be encoded.
    :return: Encoded array as numpy array
    """
    bits_per_block = max(int(array.max()).bit_length(), 2)
    binary_blocks = numpy.unpackbits(
        array.view("uint8")
    ).reshape(-1, bits_per_block)[:, -bits_per_block:]

    return numpy.packbits(binary_blocks).view(dtype=numpy.uint64)


class Anvil2Interface(Interface):
    @staticmethod
    def is_valid(key):
        if key[0] != "anvil":
            return False
        if key[1] < 1444:
            return False
        return True

    def decode(self, data: nbt.NBTFile) -> Tuple[Chunk, numpy.ndarray]:
        cx = data["Level"]["xPos"].value
        cz = data["Level"]["zPos"].value
        blocks, palette = self._decode_blocks(data["Level"]["Sections"])
        entities = self._decode_entities(data["Level"]["Entities"])
        tile_entities = None
        return Chunk(cx, cz, blocks, entities, tile_entities, extra=data), palette

    def encode(self, chunk: Chunk, palette: numpy.ndarray) -> nbt.NBTFile:
        # TODO: sort out a proper location for this data and create from scratch each time
        data = chunk._extra
        data["Level"]["Sections"] = self._encode_blocks(chunk._blocks, palette)
        # TODO: sort out the other data in sections
        # data["Level"]["Entities"] = self._encode_entities(chunk.entities)
        return data

    def _decode_blocks(
        self, chunk_sections
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        if not chunk_sections:
            raise NotImplementedError(
                "We don't support reading chunks that never been edited in Minecraft before"
            )

        blocks = numpy.zeros((256, 16, 16), dtype=int)
        palette = [Block(namespace="minecraft", base_name="air")]

        for section in chunk_sections:
            if "Palette" not in section:  # 1.14 makes palette/blocks optional.
                continue
            height = section["Y"].value << 4

            blocks[height: height + 16, :, :] = _decode_long_array(
                section["BlockStates"].value, 4096
            ).reshape((16, 16, 16)) + len(palette)

            palette += self._decode_palette(section["Palette"])

        blocks = numpy.swapaxes(blocks.swapaxes(0, 1), 0, 2)
        palette, inverse = numpy.unique(palette, return_inverse=True)
        blocks = inverse[blocks]

        return blocks.astype(f"uint{get_smallest_dtype(blocks)}"), palette

    def _encode_blocks(self, blocks: numpy.ndarray, palette: numpy.ndarray) -> nbt.TAG_List:
        sections = nbt.TAG_List()
        for y in range(16):  # perhaps find a way to do this dynamically
            block_sub_array = blocks[:, y * 16: y * 16 + 16, :].ravel()

            sub_palette_, block_sub_array = numpy.unique(block_sub_array, return_inverse=True)
            sub_palette = self._encode_palette(palette[sub_palette_])
            if len(sub_palette) == 1 and sub_palette[0]['Name'].value == 'minecraft:air':
                continue

            section = nbt.TAG_Compound()
            section['Y'] = nbt.TAG_Byte(y)
            section['BlockStates'] = nbt.TAG_Long_Array(_encode_long_array(block_sub_array))
            section['Palette'] = sub_palette
            section['BlockLight'] = nbt.TAG_Byte_Array(numpy.zeros(2048, dtype=numpy.uint8))
            section['SkyLight'] = nbt.TAG_Byte_Array(numpy.zeros(2048, dtype=numpy.uint8))
            sections.append(section)

        return sections

    @staticmethod
    def _decode_palette(palette: nbt.TAG_List) -> list:
        blockstates = []
        for entry in palette:
            namespace, base_name = entry["Name"].value.split(":", 1)
            # TODO: handle waterlogged property
            properties = {prop: str(val.value) for prop, val in entry.get("Properties", nbt.TAG_Compound({})).items()}
            block = Block(
                namespace=namespace, base_name=base_name, properties=properties
            )
            blockstates.append(block)
        return blockstates

    @staticmethod
    def _encode_palette(blockstates: list) -> nbt.TAG_List:
        palette = nbt.TAG_List()
        for block in blockstates:
            entry = nbt.TAG_Compound()
            entry['Name'] = nbt.TAG_String(f'{block.namespace}:{block.base_name}')
            properties = entry['Properties'] = nbt.TAG_Compound()
            # TODO: handle waterlogged property
            for prop, val in block.properties.items():
                if isinstance(val, str):
                    properties[prop] = nbt.TAG_String(val)
            palette.append(entry)
        return palette

    def _decode_entities(self, entities: list) -> List[nbt.NBTFile]:
        return []
        # entity_list = []
        # for entity in entities:
        #     entity = nbt_template.create_entry_from_nbt(entity)
        #     entity = self._entity_handlers[entity["id"].value].load_entity(entity)
        #     entity_list.append(entity)
        #
        # return entity_list

    def get_translator(self, max_world_version, data: nbt.NBTFile = None) -> translators.Translator:
        if data is None:
            return translators.get_translator(max_world_version)
        else:
            return translators.get_translator(("anvil", data["DataVersion"].value))


INTERFACE_CLASS = Anvil2Interface
