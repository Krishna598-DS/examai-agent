# app/tools/vector_store.py
from typing import List
from app.tools.pdf_reader import PDFChunk
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class VectorStore:

    def __init__(self):
        logger.info("vector_store_initializing")

        from sentence_transformers import SentenceTransformer
        import chromadb

        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("embedding_model_loaded", model=EMBEDDING_MODEL_NAME)

        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
        )

        self.collection = self.client.get_or_create_collection(
            name="exam_content",
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(
            "vector_store_ready",
            collection="exam_content",
            existing_documents=self.collection.count()
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.embedding_model.encode(
            texts,
            convert_to_numpy=False,
            show_progress_bar=len(texts) > 10
        )
        return [e.tolist() for e in embeddings]

    def add_chunks(self, chunks: List[PDFChunk]) -> int:
        if not chunks:
            return 0

        existing_ids = set(self.collection.get()["ids"])
        new_chunks = []
        for chunk in chunks:
            chunk_id = f"{chunk.source}_chunk_{chunk.chunk_index}"
            if chunk_id not in existing_ids:
                new_chunks.append((chunk_id, chunk))

        if not new_chunks:
            logger.info("chunks_already_indexed")
            return 0

        texts = [chunk.text for _, chunk in new_chunks]
        embeddings = self.embed_texts(texts)

        self.collection.add(
            ids=[chunk_id for chunk_id, _ in new_chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "source": chunk.source,
                    "page": chunk.page,
                    "chunk_index": chunk.chunk_index,
                }
                for _, chunk in new_chunks
            ]
        )

        logger.info("indexing_completed", chunks_added=len(new_chunks))
        return len(new_chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str = None
    ) -> List[dict]:
        if self.collection.count() == 0:
            logger.warning("search_on_empty_collection")
            return []

        query_embedding = self.embed_texts([query])[0]
        where = {"source": source_filter} if source_filter else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        formatted = []
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            similarity = 1 - distance
            formatted.append({
                "text": doc,
                "source": meta["source"],
                "page": meta["page"],
                "similarity": round(similarity, 3),
            })

        logger.info("search_completed",
                   query=query[:50],
                   results_found=len(formatted))
        return formatted

    def get_stats(self) -> dict:
        return {
            "total_chunks": self.collection.count(),
            "collection_name": "exam_content",
            "embedding_model": EMBEDDING_MODEL_NAME,
        }


vector_store = VectorStore()
