"""
Text embedding generation utility
"""
import numpy as np
import httpx
from typing import List, Optional
import hashlib
from sentence_transformers import SentenceTransformer

from config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generate text embeddings using various models"""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or self._get_default_model()
        self.httpx_client = None
        self.local_model = None
        
        # Initialize based on model type
        if "text-embedding" in self.model_name and settings.openai_api_key:
            self.httpx_client = httpx.AsyncClient(timeout=30.0)
        else:
            # Use local sentence transformer
            self._initialize_local_model()
    
    def _get_default_model(self) -> str:
        """Get default embedding model"""
        if settings.openai_api_key:
            return "text-embedding-3-small"
        else:
            return "all-MiniLM-L6-v2"  # Local sentence transformer
    
    def _initialize_local_model(self):
        """Initialize local sentence transformer model"""
        try:
            self.local_model = SentenceTransformer(self.model_name)
            logger.info(f"Initialized local embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize local model: {str(e)}")
            # Fallback to a simpler model
            self.model_name = "all-MiniLM-L6-v2"
            self.local_model = SentenceTransformer(self.model_name)
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self._get_embedding_dimension())
        
        # Normalize text
        text = text.strip()
        
        if self.httpx_client:
            return await self._generate_openai_embedding(text)
        else:
            return self._generate_local_embedding(text)
    
    async def generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
        if self.httpx_client:
            return await self._generate_openai_embeddings(texts)
        else:
            return [self._generate_local_embedding(text) for text in texts]
    
    async def _generate_openai_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using OpenAI API"""
        try:
            response = await self.httpx_client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": text,
                    "model": self.model_name,
                    "encoding_format": "float"
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            embedding = np.array(result["data"][0]["embedding"])
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {str(e)}")
            # Fallback to local model
            return self._generate_local_embedding(text)
    
    async def _generate_openai_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts using OpenAI API"""
        try:
            # OpenAI supports batch embedding
            response = await self.httpx_client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": texts,
                    "model": self.model_name,
                    "encoding_format": "float"
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Sort by index to maintain order
            embeddings_data = sorted(result["data"], key=lambda x: x["index"])
            embeddings = [np.array(item["embedding"]) for item in embeddings_data]
            
            return embeddings
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {str(e)}")
            # Fallback to local model
            return [self._generate_local_embedding(text) for text in texts]
    
    def _generate_local_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using local sentence transformer"""
        if not self.local_model:
            self._initialize_local_model()
        
        try:
            # Generate embedding
            embedding = self.local_model.encode(text, convert_to_numpy=True)
            return embedding
            
        except Exception as e:
            logger.error(f"Local embedding generation failed: {str(e)}")
            # Fallback to hash-based embedding
            return self._generate_hash_embedding(text)
    
    def _generate_hash_embedding(self, text: str) -> np.ndarray:
        """Generate a deterministic embedding using hashing (fallback)"""
        # This is a very basic fallback - not suitable for production
        dimension = self._get_embedding_dimension()
        
        # Create multiple hashes for different dimensions
        embeddings = []
        for i in range(dimension):
            hash_input = f"{text}_{i}".encode('utf-8')
            hash_value = hashlib.sha256(hash_input).hexdigest()
            # Convert hash to float between -1 and 1
            value = (int(hash_value[:8], 16) / (2**32 - 1)) * 2 - 1
            embeddings.append(value)
        
        embedding = np.array(embeddings)
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding
    
    def _get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for current model"""
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
        }
        
        return model_dimensions.get(self.model_name, 384)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.httpx_client:
            await self.httpx_client.aclose() 