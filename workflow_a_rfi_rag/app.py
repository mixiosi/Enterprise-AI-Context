import os
import streamlit as st
import traceback
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

os.environ["TOKENIZERS_PARALLELISM"] = "false"
load_dotenv()

st.set_page_config(page_title="RFI Context Engine", page_icon="🏗️")
st.title("🏗️ Workflow A: RFI Context Engine")
st.markdown("Reduces RFI manual document search from 60-180 minutes down to 10-20 minutes.")

# The Skyscraper "Penthouse" Prompt
PENTHOUSE_SYSTEM_PROMPT = """
You are 'EnterpriseAI', the AI Orchestrator for High-Performance Computing Data Centers.
NON-NEGOTIABLE RULES:
1. NEVER expose PII.
2. Prioritize OSHA standard compliance above all cost-saving measures.
3. If an RFI asks about structural integrity or cooling loops, cite your source exactly.

Use the retrieved context to answer the question. If you don't know, say you don't know.
Context:
{context}
"""

@st.cache_resource(show_spinner="Loading Enterprise Embedding Model (Local CPU)...")
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': False}
    )

# List available mock documents
MOCK_DOCS_DIR = os.path.join(os.path.dirname(__file__), "mock_documents")
available_docs = []
if os.path.exists(MOCK_DOCS_DIR):
    available_docs = [f for f in os.listdir(MOCK_DOCS_DIR) if f.endswith(".pdf")]

with st.sidebar:
    st.header("📂 Ingestion Layer (The Lower Floors)")
    st.info("Select one or more documents to build the context database.")
    selected_docs = st.multiselect("Select Blueprints / OSHA Specs", available_docs, default=available_docs)

api_key = os.environ.get("OPENROUTER_API_KEY")

if not api_key:
    st.warning("⚠️ OPENROUTER_API_KEY not found in environment variables. Please add it to your .env file.")
    st.stop()

if "rfi_db" not in st.session_state:
    st.session_state.rfi_db = None
if "last_uploaded" not in st.session_state:
    st.session_state.last_uploaded = None

# Create a stable identifier for the current selection
selection_id = ",".join(sorted(selected_docs))

if selected_docs:
    # Only process if the selection changed or we don't have a DB yet
    if st.session_state.rfi_db is None or st.session_state.last_uploaded != selection_id:
        with st.spinner(f"Processing {len(selected_docs)} document(s) into Vector Database..."):
            try:
                all_splits = []
                for doc_name in selected_docs:
                    doc_path = os.path.join(MOCK_DOCS_DIR, doc_name)
                    loader = PyPDFLoader(doc_path)
                    docs = loader.load()
                    
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    splits = text_splitter.split_documents(docs)
                    all_splits.extend(splits)
                
                embeddings = get_embeddings()
                
                # Create a fresh Chroma DB in memory with all selected documents
                st.session_state.rfi_db = Chroma.from_documents(documents=all_splits, embedding=embeddings)
                st.session_state.last_uploaded = selection_id
                st.sidebar.success(f"✅ Context Loaded: {len(selected_docs)} document(s)")
            except Exception as e:
                st.sidebar.error(f"Error processing documents: {e}")
                st.sidebar.error(traceback.format_exc())
    else:
        st.sidebar.success(f"✅ Context Loaded: {len(selected_docs)} document(s)")

if query := st.chat_input("E.g., What is the required pipe thickness for the secondary cooling loop?"):
    st.chat_message("user").write(query)
    
    if st.session_state.rfi_db is None or not selected_docs:
        st.error("Select at least one document from the sidebar first.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Accessing Skyscraper Context..."):
                try:
                    llm = ChatOpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=api_key,
                        model="openrouter/auto", 
                        temperature=0
                    )
                    # Increase k to retrieve more chunks since we have multiple documents
                    retriever = st.session_state.rfi_db.as_retriever(search_kwargs={"k": 6})
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", PENTHOUSE_SYSTEM_PROMPT),
                        ("human", "{input}"),
                    ])
                    
                    question_answer_chain = create_stuff_documents_chain(llm, prompt)
                    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                    
                    response = rag_chain.invoke({"input": query})
                    
                    # Format citations to include the document name
                    citations = set()
                    for doc in response["context"]:
                        source = os.path.basename(doc.metadata.get("source", "Unknown"))
                        page = doc.metadata.get("page", -1) + 1
                        citations.add(f"{source} (Page {page})")
                        
                    st.write(response["answer"])
                    st.caption(f"📚 Sourced from: {', '.join(sorted(citations))}")
                except Exception as e:
                    st.error(f"Error answering query: {e}")
                    st.error(traceback.format_exc())
