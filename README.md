# AI-Powered CTI Analyst & MITRE ATT&CK Scraper

A suite of Python scripts and a Streamlit chat application for working with STIX/MITRE ATT&CK data. This project leverages local LLMs (via **Ollama**) and vector databases (**ChromaDB**) to provide an AI-driven Cyber Threat Intelligence (CTI) assistant.

**Quick Summary**
- **Purpose:** Parse and ingest STIX/ATT&CK data into a vector database, then query it using an intent-routed AI chatbot.
- **AI Integrations:** Local LLM inference via **Ollama** (`qwen3:8b` for generation/intent classification) and `nomic-embed-text` for document embeddings.
- **Language:** Python

**Repository Contents**

- [stixscrape2.py](stixscrape2.py) — Parses STIX data, generates vector embeddings using Ollama, and populates a local ChromaDB instance.
- [chat2.py](chat2.py) — The main Streamlit AI Chatbot interface. Features intent classification (Factual, Analytical, Exploratory) and live external CTI search via DuckDuckGo.
- [stixscrape.py](stixscrape.py) — Legacy scraping utility.
- [chat.py](chat.py) — Basic earlier iteration of the chat endpoint.
- [enterprise-attack.json](enterprise-attack.json) — Local snapshot of the MITRE ATT&CK dataset.

**Key Features**

- **AI-Powered Semantic Search:** Uses LangChain and Ollama embeddings (`nomic-embed-text`) to semantically ground the threat intel.
- **Intent-Routed Chat:** The LLM (`qwen3:8b`) determines if a query is factual, analytical, or exploratory, dynamically adjusting context windows and prompting.
- **RAG + Live Intel:** Fallbacks to live web searches for recent threats (e.g., zero-days, latest CVEs) via DuckDuckGo if the LLM detects "recent" keywords.

**Requirements & Prerequisites**
1. **Python 3.8+**
2. **Ollama:** You must have an active Ollama environment available:
   - For Embeddings: Expected at `http://localhost:11434` running `nomic-embed-text`.
   - For LLM Inference: Expected at `http://192.168.4.50:11434` running `qwen3:8b`. *(You can modify these IP scopes inside `chat2.py` if running entirely local).*

**Installation (quick)**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Usage Examples**

1. **Ingest Data (First Time)**
   This reads the `enterprise-attack.json` file, generates structured embeddings using LangChain/Ollama, and saves them to `mitre_db/`.
   ```bash
   python stixscrape2.py
   ```

2. **Run the AI CTI Chatbot**
   Launch the interactive Streamlit assistant.
   ```bash
   streamlit run chat2.py
   ```

**Data & Database**

- The `mitre_db/` folder is generated on the first ingest and serves as the local ChromaDB. 

**Development & CI**

- This repository includes a basic GitHub Actions CI workflow at [.github/workflows/ci.yml](.github/workflows/ci.yml) that verifies Python syntax.
- MIT License is provided.

