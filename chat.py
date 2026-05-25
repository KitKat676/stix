import chromadb
import streamlit as st
from langchain_ollama import ChatOllama, OllamaEmbeddings
from chromadb.utils import embedding_functions

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

    if intent == "FACTUAL":
        results = collection.query(query_texts=[prompt], n_results=1)
    else:
        results = collection.query(query_texts=[prompt], n_results=5)

    context = "\n".join(results['documents'][0])

    print(f"Context: {context}")

    system_prompt = f"""You are a CTI analyst.
    Intent: {intent}
    Use this context to answer: "{context}"
    If the intent is ANALYTICAL, provide a structured breakdown.
    If FACTUAL< be concise. If the context is empty, say so."""

    response = llm.invoke([("system", system_prompt), ("human", prompt)])
    st.chat_message("assistant").markdown(response.content)
