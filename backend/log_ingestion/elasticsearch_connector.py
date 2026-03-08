import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

class ElasticsearchConnector:
    def __init__(self):
        self.es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        self.index_name = "kaali-logs"
        self.es = Elasticsearch([self.es_url])
        self._ensure_index_exists()

    def _ensure_index_exists(self):
        """Creates the index if it does not exist."""
        try:
            if not self.es.indices.exists(index=self.index_name):
                # Defining a basic mapping for our fields
                mapping = {
                    "mappings": {
                        "properties": {
                            "timestamp": {"type": "date"},
                            "source_ip": {"type": "ip"},
                            "username": {"type": "keyword"},
                            "event_type": {"type": "keyword"},
                            "status": {"type": "keyword"},
                            "raw_log": {"type": "text"}
                        }
                    }
                }
                self.es.indices.create(index=self.index_name, body=mapping)
                print(f"[*] Created Elasticsearch index: {self.index_name}")
            else:
                print(f"[*] connected to Elasticsearch index: {self.index_name}")
        except Exception as e:
            print(f"[!] Error connecting to or creating Elasticsearch index: {e}")

    def index_log(self, log_data: dict):
        """Indexes a single parsed log JSON object into Elasticsearch."""
        try:
            response = self.es.index(index=self.index_name, document=log_data)
            return response
        except Exception as e:
            print(f"[!] Warning: Failed to index log to Elasticsearch: {e}")
            return None
