import os
from dotenv import load_dotenv
import pandas as pd

from langchain.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import DocArrayInMemorySearch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA

def main():
    # Load environment variables
    load_dotenv()
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # === Load CSV as LangChain documents ===
    csv_path = "data/csv/Python_jobstreet_2025-08-31_192232"  # Updated csv path separators
    loader = CSVLoader(file_path=csv_path, encoding="utf-8")
    documents = loader.load()

    # === Split documents into chunks ===
    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=80)
    docs = splitter.split_documents(documents)

    # === Create vectorstore (DocArrayInMemorySearch) ===
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    vectorstore = DocArrayInMemorySearch.from_documents(docs, embedding=embeddings)

    # === Initialize LLM (Deepseek) ===
    llm = ChatOpenAI(
        model="deepseek/deepseek-chat-v3.1:free",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0
    )

    # === Build RAG RetrievalQA chain ===
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True
    )

    # === Interactive Q&A ===
    print("\nRAG ready! Ask questions about your CSV/Excel. Type 'exit' to quit.\n")

    while True:
        try:
            question = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if question.lower() in {"exit", "quit", ""}:
            print("Bye!")
            break

        result = qa({"query": question})
        print("\nA:", result.get("result", "No answer"), "\n")

        # Show sources
        sources = result.get("source_documents", [])
        if sources:
            print("Sources:")
            for i, doc in enumerate(sources, 1):
                src = doc.metadata.get("source", "?")
                row = doc.metadata.get("row", "?")
                print(f"  [{i}] {src} (row {row})")
        print("\n" + "-" * 60 + "\n")

if __name__ == '__main__':
    main()