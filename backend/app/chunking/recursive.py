from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.chunking.base import Chunker


class RecursiveChunker(Chunker):

    def __init__(
        self,
        chunk_size: int = 300,
        chunk_overlap: int = 50,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(
        self,
        text: str
    ) -> list[str]:

        return self.splitter.split_text(text)
