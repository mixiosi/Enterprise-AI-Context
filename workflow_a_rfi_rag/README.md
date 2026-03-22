# Workflow A: RFI Context Engine (RAG Pipeline)

This document provides a detailed, component-level view of how the **Retrieval-Augmented Generation (RAG)** pipeline operates for the Request for Information (RFI) Context Engine. 

By running the embedding models locally and only sending retrieved snippets to the LLM, we ensure that our massive, proprietary construction blueprints and OSHA specifications never leak entirely to a third-party API.

## Architecture Diagram

```mermaid
sequenceDiagram
    autonumber
    
    actor Engineer as Site Engineer
    participant UI as Streamlit Interface
    
    box Local Network (Secure)
        participant Loader as PyPDF / Splitter
        participant Embed as HF Embeddings (CPU)
        participant VDB as ChromaDB (Vector)
    end
    
    box Cloud
        participant LLM as OpenRouter / LLM
    end

    %% Document Ingestion Phase
    Note over Engineer, VDB: Phase 1: Document Ingestion (Offline/Local)
    Engineer->>UI: Selects PDF(s) (e.g., Cooling Specs)
    UI->>Loader: Extracts text from PDFs
    Loader->>Loader: Chunks text (1000 chars, 200 overlap)
    Loader->>Embed: Sends chunks for vectorization
    Embed-->>Loader: Returns mathematical vectors (384 dimensions)
    Loader->>VDB: Stores vectors + page metadata
    VDB-->>UI: Confirm DB initialization
    UI-->>Engineer: "Context Loaded"

    %% Query Phase
    Note over Engineer, LLM: Phase 2: RFI Query & Generation
    Engineer->>UI: Submits Query ("Pipe thickness?")
    UI->>Embed: Embeds the user's text query
    Embed-->>UI: Returns query vector
    UI->>VDB: Performs Semantic Search (Top-K=6)
    VDB-->>UI: Returns most relevant PDF chunks
    
    %% Orchestration
    UI->>LLM: Sends [System Prompt + Context Chunks + Query]
    LLM-->>UI: Returns synthesized answer
    
    %% Formatting
    UI->>UI: Extracts metadata (Source Doc + Page #)
    UI-->>Engineer: Displays final answer with exact citations
```

## Technical Flow Breakdown

1. **Ingestion Layer:** When a user selects a document, `PyPDFLoader` strips the raw text. The `RecursiveCharacterTextSplitter` chops this massive text into overlapping chunks of 1000 characters so no context is lost at the boundaries.
2. **Local Embedding:** To save costs and maximize security, the chunks are converted into vector representations using a local HuggingFace model (`all-MiniLM-L6-v2`) running purely on the CPU.
3. **Vector Storage:** These vectors, alongside their original text and metadata (page numbers, document names), are stored in an in-memory `ChromaDB` instance.
4. **Retrieval & Synthesis:** When the engineer asks a question, the app embeds their question, compares it against the database, and pulls the top 6 most relevant chunks. The LLM then reads those specific chunks and synthesizes an accurate answer, forced by its System Prompt to cite its sources.
