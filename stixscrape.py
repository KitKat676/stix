import chromadb
from langchain_community.document_loaders import JSONLoader
from langchain_ollama import OllamaEmbeddings
from chromadb.utils import embedding_functions
from mitreattack.stix20 import MitreAttackData 
#from mitreattack.stix20 import MityreAttackData import chromadb

mitre_data = MitreAttackData("enterprise-attack.json")

embedding_func = embedding_functions.OllamaEmbeddingFunction(model_name="nomic-embed-text")

client = chromadb.PersistentClient(path="./mitre_db")
collection = client.get_or_create_collection(name="mitre_attack", embedding_function=embedding_func)

techniques = mitre_data.get_techniques() 

for t in techniques:
    tactics = []
    if hasattr(t, 'kill_chain_phases'):
        for phase in t.kill_chain_phases:
            if phase['kill_chain_name'] == 'mitre-attack':
                tactics.append(phase['phase_name'])


attack_id = mitre_data.get_attack_id(t.id)
doc_content = f"Technique: {t.name} ({attack_id})\n\n{t.description}"

documents = []
metadatas = []
ids = []
documents.append(doc_content)
metadatas.append({"name": t.name, "attack_id":attack_id,
                  "type": "technique",
                  "tactics": ",".join(tactics)
                  })

ids.append(t.id)

collection.add(documents=documents, metadatas=metadatas, ids=ids)
print("Ingestion complete!")
