import os
from functools import lru_cache
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from src.config import logger

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    logger.warning("PINECONE_API_KEY no encontrada en variables de entorno.")

pc = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None
index_host = os.getenv("PINECONE_INDEX_HOST", "https://uclm-corpus-roma-dptaw1c.svc.aped-4627-b74a.pinecone.io")
index = pc.Index(host=index_host) if pc else None

embed_model = None
try:
    logger.info("Cargando modelo de embeddings 'all-MiniLM-L6-v2'...")
    embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"Error cargando modelo de embeddings: {e}")

@lru_cache(maxsize=100)
def hybrid_search_engine_cached(user_query: str, top_k: int = 10) -> str:
    """Retrieve context from Pinecone using hybrid search with cache."""
    if not index or not embed_model:
        return ""
    try:
        query_emb = embed_model.encode(user_query).tolist()
        results = index.query(
            vector=query_emb,
            top_k=top_k,
            include_metadata=True
        )
        context = "\n\n".join([m['metadata'].get('text', '') for m in results.get('matches', [])])
        return context[:4000]  # Limit context size
    except Exception as e:
        logger.error(f"Error en búsqueda vectorial (Pinecone): {e}")
        return ""

def retrieve_context(query: str, top_k: int = 5) -> str:
    """Wrapper para recuperar el corpus legal experto de Pinecone."""
    return hybrid_search_engine_cached(query, top_k)
