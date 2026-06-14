import re
import pandas as pd
from datasets import load_dataset

class AviationTextNormalizer:
    def __init__(self):
        # Dictionary of critical aviation acronyms to expand
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
        # Converts FL300 into flight level 30000 feet
        pattern = r"\bfl(\d{2,3})\b"
        return re.sub(pattern, lambda m: f"flight level {int(m.group(1)) * 100} feet", text)

    def normalize_acronyms(self, text):
        # Replaces exact matches of acronyms with their expanded forms
        words = text.split()
        normalized_words = [self.acronym_map.get(word, word) for word in words]
        return " ".join(normalized_words)

    def process_narrative(self, raw_text):
        if not raw_text or not isinstance(raw_text, str):
            return ""
        
        # Convert to lowercase for uniform processing
        text = raw_text.lower()
        
        # Apply structured regex expansions
        text = self.expand_flight_levels(text)
        
        # Normalize standalone acronym tokens
        text = self.normalize_acronyms(text)
        
        # Remove extra whitespace noise
        text = re.sub(r"\s+", " ", text).strip()
        return text

def run_ingestion_pipeline(limit=100):
    print("Initializing ASRS Dataset Ingestion...")
    
    # Load the specified dataset from Hugging Face
    # We use streaming=True to avoid loading gigabytes into RAM all at once
    dataset = load_dataset("elihoole/asrs-aviation-reports", split="train", streaming=True)
    
    normalizer = AviationTextNormalizer()
    processed_records = []
    
    print("Streaming and processing records...")
    for i, record in enumerate(dataset):
        if i >= limit:
            break
            
        # Extract the primary narrative and metadata
        raw_narrative = record.get("narrative", "")
        synopsis = record.get("synopsis", "")
        meta_id = record.get("id", f"AC-{i}")
        
        # Clean the text using our normalization engine
        cleaned_narrative = normalizer.process_narrative(raw_narrative)
        
        # Construct the processed payload
        processed_payload = {
            "record_id": meta_id,
            "raw_text": raw_narrative,
            "cleaned_text": cleaned_narrative,
            "synopsis": synopsis,
            "metadata": {
                "length": len(cleaned_narrative.split())
            }
        }
        processed_records.append(processed_payload)
        
    # Convert to DataFrame to verify structural integrity
    df = pd.DataFrame(processed_records)
    print(f"Successfully processed {len(df)} records.")
    return df

if __name__ == "__main__":
    # Test the ingestion of the first 5 records
    sample_dataframe = run_ingestion_pipeline(limit=5)
    print("\nSample Processed Cleaned Text:")
    print(sample_dataframe["cleaned_text"].iloc[0][:300] + "...")