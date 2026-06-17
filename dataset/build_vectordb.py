import re
import uuid
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os

# Increase the Hugging Face hub and HTTP request timeout parameters to 5 minutes
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"  # Uses faster Rust-based download client if available
os.environ["HTTP_TIMEOUT"] = "300"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

class AviationTextNormalizer:
    def __init__(self):
        self.acronym_map = {
            "imc": "instrument meteorological conditions",
            "vfr": "visual flight rules",
            "ifr": "instrument flight rules",
            "atc": "air traffic control",
            "metar": "meteorological aerodrome report",
            "taf": "terminal aerodrome forecast",
            "ils": "instrument landing system",
            "tcas": "traffic collision avoidance system"
        }
        
    def expand_flight_levels(self, text):
        pattern = r"\bfl(\d{2,3})\b"
        return re.sub(pattern, lambda m: f"flight level {int(m.group(1)) * 100} feet", text)

    def normalize_acronyms(self, text):
        words = text.split()
        normalized_words = [self.acronym_map.get(word, word) for word in words]
        return " ".join(normalized_words)

    def process_narrative(self, raw_text):
        if not raw_text or not isinstance(raw_text, str):
            return ""
        
        text = raw_text.lower()
        text = self.expand_flight_levels(text)
        text = self.normalize_acronyms(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

def build_vector_database():
    print("Initializing components...")
    
    # 1. Load the Embedding Model
    # BGE-small is an excellent, fast open-source model for search
    print("Loading BGE embedding model...")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    vector_dimension = model.get_embedding_dimension()
    
    # 2. Initialize Qdrant Vector Database
    # Updated to point to the Dockerized Qdrant container
    print("Connecting to local Qdrant database...")
    qdrant = QdrantClient(url="http://localhost:6333")
    collection_name = "asrs_incidents"
    
    # Create the collection if it does not exist
    if not qdrant.collection_exists(collection_name):
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_dimension, distance=Distance.COSINE),
        )
        print(f"Created new collection: {collection_name}")
    
    # 3. Stream and Process the Dataset
    print("Connecting to Hugging Face dataset stream...")
    dataset = load_dataset("elihoole/asrs-aviation-reports", split="train", streaming=True)
    normalizer = AviationTextNormalizer()
    
    batch_size = 250
    payloads = []
    texts_to_embed = []
    total_inserted = 0
    
    print("Starting data ingestion and embedding...")
    
    # We remove the limit parameter to process the entire dataset
    for i, record in enumerate(dataset):
        raw_nar_1 = record.get("Report 1_Narrative", "")
        raw_nar_2 = record.get("Report 2_Narrative", "")
        synopsis = record.get("Report 1.2_Synopsis", "")
        
        if not raw_nar_1 or not synopsis:
            continue
            
        if not raw_nar_2:
            raw_nar_2 = synopsis
            
        cleaned_1 = normalizer.process_narrative(raw_nar_1)
        cleaned_2 = normalizer.process_narrative(raw_nar_2)
        combined_text = f"narrative one: {cleaned_1} | narrative two: {cleaned_2}"
        
        # Prepare the metadata payload
        payload = {
            "record_id": record.get("acn_num_ACN", f"AC-{i}"),
            "text": combined_text,
            "synopsis": synopsis,
            "aircraft_make": record.get("Aircraft 1_Make Model Name", "Unknown"),
            "event_date": record.get("Date_YYYYMM", "Unknown")
        }
        
        texts_to_embed.append(combined_text)
        payloads.append(payload)
        
        # 4. Batch Insertion Logic
        if len(texts_to_embed) >= batch_size:
            # Generate vectors for the batch
            embeddings = model.encode(texts_to_embed)
            
            # Construct Qdrant point objects
            batch_points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding.tolist(),
                    payload=payload
                )
                for embedding, payload in zip(embeddings, payloads)
            ]
            
            # Insert into database
            qdrant.upsert(
                collection_name=collection_name,
                points=batch_points
            )
            
            total_inserted += len(batch_points)
            print(f"Inserted {total_inserted} records into Qdrant...")
            
            # Clear batches to free up memory
            texts_to_embed = []
            payloads = []
            
    # Process any remaining records after the loop finishes
    if texts_to_embed:
        embeddings = model.encode(texts_to_embed)
        batch_points = [
            PointStruct(id=str(uuid.uuid4()), vector=emb.tolist(), payload=p)
            for emb, p in zip(embeddings, payloads)
        ]
        qdrant.upsert(collection_name=collection_name, points=batch_points)
        total_inserted += len(batch_points)
        
    print(f"\nPipeline Complete. Successfully indexed {total_inserted} records.")

if __name__ == "__main__":
    build_vector_database()