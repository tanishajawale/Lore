import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import logging
from .config import EMBEDDING_MODEL

class VectorStore:
    def __init__(self):
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.index = None
        self.documents = []
        self.metadata = []
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.index_path = "faiss_index.bin"
        self.data_path = "faiss_data.json"
        self._load()

    def _load(self):
        import os
        import json
        if os.path.exists(self.index_path) and os.path.exists(self.data_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                self.documents = data.get("documents", [])
                self.metadata = data.get("metadata", [])
            logging.info(f"✅ Loaded {len(self.documents)} existing chunks from persistent storage")

    def _save(self):
        import json
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
            with open(self.data_path, 'w') as f:
                json.dump({"documents": self.documents, "metadata": self.metadata}, f)
    
    def add_documents(self, processed_docs: Dict[str, List[str]]):
        """Add processed documents to the vector store."""
        for doc_name in processed_docs.keys():
            self.remove_document(doc_name)
            
        all_chunks = []
        all_metadata = []
        
        for doc_name, chunks in processed_docs.items():
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "document": doc_name,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
        
        if not all_chunks:
            logging.warning("No documents to add to vector store")
            return
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(all_chunks)
        
        # Create or update FAISS index
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.documents = all_chunks
            self.metadata = all_metadata
        else:
            self.documents.extend(all_chunks)
            self.metadata.extend(all_metadata)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype('float32'))
        
        self._save()
        logging.info(f"✅ Added {len(all_chunks)} chunks to vector store and saved to disk")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[str, Dict, float]]:
        """Search for similar documents."""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:  # Valid index
                results.append((
                    self.documents[idx],
                    self.metadata[idx],
                    float(score)
                ))
        
        return results
    
    def get_document_chunks(self, document_name: str) -> List[str]:
        """Get all chunks for a specific document."""
        chunks = []
        for i, metadata in enumerate(self.metadata):
            if metadata["document"] == document_name:
                chunks.append(self.documents[i])
        return chunks
        
    def remove_document(self, doc_name: str):
        """Remove a specific document from the vector store."""
        if not self.index:
            return
            
        # Filter out the documents and metadata
        new_docs = []
        new_meta = []
        for i, meta in enumerate(self.metadata):
            if meta["document"] != doc_name:
                new_docs.append(self.documents[i])
                new_meta.append(meta)
                
        # Rebuild index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = []
        self.metadata = []
        
        if new_docs:
            self.documents = new_docs
            self.metadata = new_meta
            embeddings = self.embedding_model.encode(new_docs)
            faiss.normalize_L2(embeddings)
            self.index.add(embeddings.astype('float32'))
            
        self._save()
    
    def get_all_documents(self) -> List[str]:
        """Get list of all document names."""
        return list(set([meta["document"] for meta in self.metadata]))
    
    def clear(self):
        """Clear the vector store."""
        import os
        self.index = None
        self.documents = []
        self.metadata = []
        
        # Clear persistent files
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.data_path):
            os.remove(self.data_path)
