import chromadb
from langchain_community.document_loaders import JSONLoader
from langchain_ollama import OllamaEmbeddings
from chromadb.utils import embedding_functions
from mitreattack.stix20 import MitreAttackData
from datetime import datetime

# Initialize data and DB
mitre_data = MitreAttackData("enterprise-attack.json")
embedding_func = embedding_functions.OllamaEmbeddingFunction(model_name="nomic-embed-text")

client = chromadb.PersistentClient(path="./mitre_db")
collection = client.get_or_create_collection(name="mitre_attack", embedding_function=embedding_func)

techniques = mitre_data.get_techniques()

documents = []
metadatas = []
ids = []
counter = 0

for t in techniques:
    # 1. Extract tactics (Your original logic)
    modified_str = getattr(t, 'modified', '2015-01-01T00:00:00.000Z')
    if modified_str is None:
        modified_date_int = 2050101
    else:
        modified_date_int = int(modified_str.strftime("%Y%m%d"))

    tactics = []
    if hasattr(t, 'kill_chain_phases'):
        for phase in t.kill_chain_phases:
            if phase['kill_chain_name'] == 'mitre-attack':
                tactics.append(phase['phase_name'])
                
    attack_id = mitre_data.get_attack_id(t.id)
    tactics_str = ",".join(tactics)

    # 2. Ingest the baseline technique text 
    # (Useful for general queries like "What is MFA bypass?")
    base_doc_content = f"Technique: {t.name} ({attack_id})\n\n{t.description}"
    documents.append(base_doc_content)
    metadatas.append({
        "name": t.name, 
        "attack_id": attack_id,
        "type": "technique_definition",
        "tactics": tactics_str,
        "modified_date" : modified_date_int
    })
    ids.append(t.id)

    # 3. THE FLATTENING: Map Groups (Threat Actors) to this Technique
    # This creates the semantic bridge between "Cozy Bear" and the technique mechanics
    groups_using_tech = mitre_data.get_groups_using_technique(t.id)
    
    # documents = []
    # metadatas = []
    # ids = []
    
    for group_dict in groups_using_tech:
        group = group_dict["object"]
        relationships = group_dict["relationships"] 
        
        group_name = group.name
        # Extract aliases (e.g., APT29, Cozy Bear, NOBELIUM)
        aliases = ", ".join(getattr(group, "aliases", [])) 
        print(aliases)
        
        for rel in relationships:
            # The relationship object often contains the precise description 
            # of HOW the group used the technique (the Procedure)
            procedure_desc = rel.get("description", "No specific procedure description provided.")
            
            # Construct the denormalized text chunk
            flat_doc = (
                f"Threat Actor Group: {group_name}\n"
                f"Known Aliases: {aliases}\n"
                f"Technique Used: {t.name} ({attack_id})\n"
                f"Tactics: {tactics_str}\n"
                f"Procedure Description: {procedure_desc}"
            )
            
            documents.append(flat_doc)
            
            # Inject rich metadata for filtering
            metadatas.append({
                "group_name": group_name,
                "aliases": aliases,
                "technique_name": t.name,
                "attack_id": attack_id,
                "type": "procedure_flattened",
                "tactics": tactics_str,
                "modified_date" : modified_date_int
            })
            
            # Use the STIX relationship ID to ensure uniqueness in Chroma
            ids.append("r"+rel.id+str(counter))
            counter+=1 

# ChromaDB handles batch adding automatically in recent versions.
# If you run into payload size limits, you can split this into batches of 40,000.
# print(len(documents), len(metadatas), len(ids))
# collection.add(documents=documents, metadatas=metadatas, ids=ids)
# print(f"Ingestion complete! Added {len(documents)} chunks to the database.")

batch_size = 1000  

# Assuming documents, metadatas, and ids are all lists of the same length
total_docs = len(documents)

for i in range(0, total_docs, batch_size):
    # Slice the lists to create a batch
    batch_docs = documents[i : i + batch_size]
    batch_meta = metadatas[i : i + batch_size]
    batch_ids = ids[i : i + batch_size]
    
    print(f"Adding batch {i} to {i + len(batch_docs)} out of {total_docs}...")
    
    # Add the current batch to ChromaDB
    collection.add(
        documents=batch_docs,
        metadatas=batch_meta,
        ids=batch_ids
    )

print("Finished adding all documents.")