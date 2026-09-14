from app.chunking.recursive import RecursiveChunker


class ChunkerFactory:

    @staticmethod
    def get_chunker():

        return RecursiveChunker()
