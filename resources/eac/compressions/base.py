from io import BufferedReader, BytesIO


class BaseCompressionAlgorithm:

    def uncompress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        pass

    def compress(self, buffer: [BufferedReader, BytesIO], input_length: int):
        pass
