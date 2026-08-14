import os
from dotenv import load_dotenv
from mem0.configs.base import MemoryConfig
from mem0 import Memory

load_dotenv(r"C:\\Users\\user\\whatsapp-bridge\\.env")

GROQ_KEY = os.getenv("GROQ_API_KEY")
HF_KEY = os.getenv("HUGGINGFACE_API_KEY")

print("GROQ key loaded:", bool(GROQ_KEY))
print("HF key loaded:", bool(HF_KEY))

config = MemoryConfig(
    embedder={"provider": "huggingface", "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"}},
    llm={"provider": "groq", "config": {"model": "llama-3.3-70b-versatile", "api_key": GROQ_KEY}},
    vector_store={"provider": "chroma", "config": {"collection_name": "hermes-memories"}},
)

m = Memory(config=config)
print("Memory initialized OK")

m.add("Riziki prefers short replies", user_id="riziki")
results = m.search("how does Riziki like replies?", filters={"user_id": "riziki"})
print("Search results:", results)
