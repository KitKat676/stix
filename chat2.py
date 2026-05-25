import chromadb
import streamlit as st
from langchain_ollama import ChatOllama, OllamaEmbeddings
from chromadb.utils import embedding_functions
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

def live_search_tool(user_prompt):
    search = DuckDuckGoSearchAPIWrapper(max_results=3)
    trusted_sites = [
            "site:cisa.gov/news-events/cybsersecurity/cybersecurity-advisories",
            "site:mandiant.com/resources/blog",
            "site:unit42.paloaltonetworks.com",
            "site:bleepingcomputer.com"
            ]

    site_filter = f"({' OR '.join(trusted_sites)})"
    combined_query = f"{site_filter}{user_prompt}"

    try:
        search_results = search.run(combined_query)
        if search_results:
            return search_results
        return "No recent external intelligence found"

    except Exception as e:
        return f"Live search failed: {str(e)}"
        return f"Live CTI search failed: {str(e)}"

embedding_func = embedding_functions.OllamaEmbeddingFunction(
        url = "http://localhost:11434/api/embeddings",
        model_name = "nomic-embed-text"
        )

client = chromadb.PersistentClient(path="./mitre_db")
collection = client.get_collection(name="mitre_attack", embedding_function=embedding_func)
llm = ChatOllama(base_url = "http://192.168.4.50:11434", model="qwen3:8b")
#llm = ChatOllama(model="llama3.2:1b")
#classifier = ChatOllama(model="llama3.2:1b")
classifier = ChatOllama(base_url = "http://192.168.4.50:11434", model="qwen3:8b")

st.title("CTI Analyst Bot (With Intent Routing)")

def detect_intent(query):
    system_prompt = """You are a CTI Intent Classifier.
    Classify the query into EXACTLY one of: FACTUAL, ANALYTICAL, EXPLORATORY.

    Factual - Requests a speciifc, discrete piece of information
    Examples:
    "What tactic does T1059 belong to?"
    "Give me the definition of Living off the Land."

    Analytical - Asks for reasoning, relationships, comparisons, or strategic insight.
    Examples:
    "How do APT29 techniques chain tigether for lateral movement"
    "What's the difference between T1078 and T1133"
    "Why would an attacker use LOLBins instead of custom malware?"

    Exploratory - Broad discovery; the user doesn;t know what they're looking for yet
    Examples:
    "What techniques target credentials?"
    "Show me persistence techniques on Windows"

    Rules:
    - If the query contains a speciifc ID or named technique and asks WHAT it is => Factual
    - If the query asks WHY or HOW or to COMPARE -> Analytical
    - If the query asks WHAT EXISTS or ShOW ME -> Exploratory
    Return ONLY the category name, no explanation

    """

    response = classifier.invoke([("system", system_prompt), ("human", query)])
    return response.content.strip().upper()

if prompt := st.chat_input("Ask about a TTP..."):
        st.chat_message("user").markdown(prompt)
    
        intent = detect_intent(prompt)
    
        st.sidebar.info(f"Detected Intent: {intent}")
    
        context = ""

    # Adjust recall based on intent.
        # Since flattened data creates more chunks, bump ANALYTICAL/EXPLORATORY to 7 or 8
        if intent == "FACTUAL":
            results = collection.query(query_texts=[prompt], n_results=1)
            context = "\n".join(results['documents'][0])
        else:
            results = collection.query(query_texts=[prompt], n_results=15)
            mitre_results = collection.query(query_texts=[prompt], n_results=4)
            mitre_context = "\n".join(mitre_results['documents'][0])
            recent_keywords = ["latest", "recent", "cve-", "zero-day", "new technique", "2026"]
            if any(keyword in prompt.lower() for keyword in recent_keywords):
                st.sidebar.warning("Fetchingi live external inteliigence")
                live_context = live_search_tool(prompt)

                context = (
                        f"---START OFFICIAL MITRE MATRIX BASELINE --- \n{mitre_context}\n"
                        f"---START RECENT LIVE INTEL ---\n{live_context}"
                        )
            else:
                context = mitre_context

            if intent == "ANALYTICAL" and "latest" in prompt:
                mitre_context = get_chroma_context(prompt)
                live_context = live_search_tool(f"site:cisa.gov/news-events/cybsersecurity/cybersecurity-advisories {prompt}")
                context = f"Official MITRE Background: \n{mitre_context}\n\nRecent Live Intelligence: \n {live_context}"
    
        # Reconstruct a highly structured context using metadata
        context_chunks = []

        extracted_results = []
        for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
            extracted_results.append({
                "document": doc,
                "metadata": meta,
                "distance": dist
                })

        for er in extracted_results:
            print(er['metadata'].keys())
        sorted_results = sorted(extracted_results, 
                                key=lambda x: (x['metadata']['modified_date'], -x['distance']), 
                                reverse = True)

        top_results = sorted_results[:5]
        context = "\n---\n".join(item['document'] for item in top_results)
    
        if results and results['documents'] and len(results['documents'][0]) > 0:
            for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                if meta["type"] == "technique_definition":
                    context_chunks.append(f"=== BASE TECHNIQUE DEFINITION ===\n{doc}\n")
                elif meta["type"] == "procedure_flattened":
                    context_chunks.append(
                        f"=== OBSERVED THREAT ACTOR BEHAVIOR ===\n"
                        f"Actor: {meta.get('group_name', 'Unknown')}\n"
                        f"{doc}\n"
                    )
            context = "\n-----------------------\n".join(context_chunks)
        else:
            context = ""
    
        print(f"Context Sent to LLM:\n{context}")
    
        # Refined system prompt that forces the LLM to respect the metadata boundaries
        system_prompt = f"""You are an expert Cyber Threat Intelligence (CTI) analyst.
    
        The user's intent is classified as: {intent}
    
        Review the structured context below. It contains both baseline MITRE ATT&CK technique definitions and flattened, observed procedures tied to specific threat groups.
    
        CONTEXT:
        {context}
    
        INSTRUCTIONS:
        1. Base your answer strictly on the provided context.
        2. If the user asks about a specific group (e.g., Cozy Bear), prioritize the 'OBSERVED THREAT ACTOR BEHAVIOR' sections.
        3. If the intent is ANALYTICAL, deliver a structured, technical breakdown of the relationships or mechanics.
        4. If the intent is FACTUAL, be direct and concise.
        5. If the context does not contain enough information to answer the question reliably, explicitly state that you lack sufficient data in the current corpus."""
    
        response = llm.invoke([("system", system_prompt), ("human", prompt)])
        st.chat_message("assistant").markdown(response.content)
