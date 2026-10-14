from io import BufferedReader, BytesIO
from typing import List


class BaseCompressionAlgorithm:
    # aliases of the games (`library.read_blocks.misc.compatibility.GAMES`) that read this algorithm
    # (resources/eac_compressions.md)
    target_games: List[str] = []

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        pass

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        pass
