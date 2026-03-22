import os
import streamlit as st
import tempfile
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

@st.cache_resource(show_spinner="Loading Enterprise Embedding Model (Local)...")
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

with st.sidebar:
    st.header("📂 Ingestion Layer (The Lower Floors)")
    uploaded_file = st.file_uploader("Upload Blueprint / OSHA Spec (PDF)", type="pdf")

api_key = os.environ.get("OPENROUTER_API_KEY")

if not api_key:
    st.warning("⚠️ OPENROUTER_API_KEY not found in environment variables. Please add it to your .env file.")
    st.stop()

if "rfi_db" not in st.session_state:
    st.session_state.rfi_db = None
if "last_uploaded" not in st.session_state:
    st.session_state.last_uploaded = None

if uploaded_file:
    # Only process if it's a new file or we don't have a DB yet
    if st.session_state.rfi_db is None or st.session_state.last_uploaded != uploaded_file.name:
        with st.spinner("Processing document into Vector Database..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                loader = PyPDFLoader(tmp_path)
                docs = loader.load()
                
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                splits = text_splitter.split_documents(docs)
                
                embeddings = get_embeddings()
                
                # Create a fresh Chroma DB in memory
                st.session_state.rfi_db = Chroma.from_documents(documents=splits, embedding=embeddings)
                st.session_state.last_uploaded = uploaded_file.name
                st.sidebar.success("✅ Context Loaded into Local ChromaDB!")
            except Exception as e:
                st.sidebar.error(f"Error processing document: {e}")
                st.sidebar.error(traceback.format_exc())
    else:
        st.sidebar.success("✅ Context Loaded into Local ChromaDB!")

if query := st.chat_input("E.g., What is the required pipe thickness for the secondary cooling loop?"):
    st.chat_message("user").write(query)
    
    if st.session_state.rfi_db is None:
        st.error("Upload a document first.")
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
                    retriever = st.session_state.rfi_db.as_retriever(search_kwargs={"k": 4})
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", PENTHOUSE_SYSTEM_PROMPT),
                        ("human", "{input}"),
                    ])
                    
                    question_answer_chain = create_stuff_documents_chain(llm, prompt)
                    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
                    
                    response = rag_chain.invoke({"input": query})
                    
                    citations = {str(doc.metadata.get("page", -1) + 1) for doc in response["context"]}
                    st.write(response["answer"])
                    st.caption(f"📚 Sourced from Page(s): {', '.join(sorted(citations))}")
                except Exception as e:
                    st.error(f"Error answering query: {e}")
                    st.error(traceback.format_exc())
