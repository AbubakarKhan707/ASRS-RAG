import re
import pandas as pd
from datasets import load_dataset

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

def run_ingestion_pipeline(limit=100):
    print("Initializing ASRS Ingestion with Data Imputation...")
    
    dataset = load_dataset("elihoole/asrs-aviation-reports", split="train", streaming=True)
    normalizer = AviationTextNormalizer()
    processed_records = []
    
    # Telemetry variables to track our data quality pipeline
    dropped_count = 0
    imputed_count = 0
    
    print("Streaming and processing records...")
    for i, record in enumerate(dataset):
        if i >= limit:
            break
            
        # Extract the relevant fields based on the dataset schema
        raw_narrative_1 = record.get("Report 1_Narrative", "")
        raw_narrative_2 = record.get("Report 2_Narrative", "")
        synopsis = record.get("Report 1.2_Synopsis", "")
        meta_id = record.get("acn_num_ACN", f"AC-{i}")
        
        # 1. The Strict Filter Strategy
        # If the primary narrative or the expert synopsis is missing, drop the row
        if not raw_narrative_1 or not synopsis:
            dropped_count += 1
            continue
            
        # 2. The Semantic Fallback Strategy
        # If the second narrative is missing, inject the synopsis in its place
        if not raw_narrative_2:
            raw_narrative_2 = synopsis
            imputed_count += 1
            
        # Clean both narratives
        cleaned_nar_1 = normalizer.process_narrative(raw_narrative_1)
        cleaned_nar_2 = normalizer.process_narrative(raw_narrative_2)
        
        # Combine them into a single dense chunk for the vector database
        combined_text = f"narrative one: {cleaned_nar_1} | narrative two: {cleaned_nar_2}"
        
        processed_payload = {
            "record_id": meta_id,
            "cleaned_text": combined_text,
            "synopsis": synopsis,
            "metadata": {
                "imputed_narrative_2": not bool(record.get("Report 2_Narrative", ""))
            }
        }
        processed_records.append(processed_payload)
        
    df = pd.DataFrame(processed_records)
    print(f"Pipeline Complete -> Scanned: {limit} | Kept: {len(df)} | Dropped: {dropped_count} | Imputed: {imputed_count}")
    return df

if __name__ == "__main__":
    # Test a larger batch to see the drop/impute ratio in action
    sample_dataframe = run_ingestion_pipeline(limit=50)
    print("\nSample Output of First Kept Record:")
    print(sample_dataframe["cleaned_text"].iloc[0][:400] + "...")