import os
import json
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.chat_models import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_qdrant import Qdrant
from langchain.prompts import ChatPromptTemplate


# === Step 1: Parse query into filters ===
def parse_query_to_filters(llm, query: str):
    prompt = ChatPromptTemplate.from_template("""
    Extract structured filters from this query: "{query}"

    Rules:
    - If a specific date is mentioned (e.g. "August 30", "yesterday"), convert it to ISO format "YYYY-MM-DD".
    - If a relative time period is mentioned (e.g. "past week", "last 30 days"), set "date_range" to the number of days.
    - If no date is provided, set both "date_listed" and "date_range" to null.

    Return JSON with possible keys:
    - job_title: string or null
    - company: string or null
    - location: string or null
    - work_arrangement: string or null (e.g. remote, onsite, hybrid)
    - date_listed: string or null (ISO format YYYY-MM-DD)
    - date_range: integer or null (number of days, e.g. 7 for past week)
    - link: string or null
    - job_details: string or null
    """)
    response = llm.invoke(prompt.format(query=query))
    try:
        return json.loads(response.content)
    except Exception:
        return {
            "job_title": None,
            "company": None,
            "location": None,
            "work_arrangement": None,
            "date_listed": None,
            "date_range": None,
            "link": None,
            "job_details": None,
        }


# === Step 2: Convert filters to Qdrant-compatible filter ===
def build_qdrant_filter(filters):
    must_conditions = []

    if filters.get("job_title"):
        must_conditions.append({"key": "job_title", "match": {"value": filters["job_title"]}})
    if filters.get("company"):
        must_conditions.append({"key": "company", "match": {"value": filters["company"]}})
    if filters.get("location"):
        must_conditions.append({"key": "location", "match": {"value": filters["location"]}})
    if filters.get("work_arrangement"):
        must_conditions.append({"key": "work_arrangement", "match": {"value": filters["work_arrangement"]}})
    if filters.get("date_listed"):
        must_conditions.append({"key": "date_listed", "match": {"value": filters["date_listed"]}})
    if filters.get("date_range"):
        cutoff_date = (datetime.now() - timedelta(days=int(filters["date_range"]))).strftime("%Y-%m-%d")
        must_conditions.append({"key": "date_listed", "range": {"gte": cutoff_date}})
    if filters.get("link"):
        must_conditions.append({"key": "link", "match": {"value": filters["link"]}})
    if filters.get("job_details"):
        must_conditions.append({"key": "job_details", "match": {"value": filters["job_details"]}})

    return {"must": must_conditions} if must_conditions else None


# === Step 3: Build documents only if needed ===
def build_documents_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []
    for _, row in df.iterrows():
        job_details = str(row.get("job_details", ""))
        chunks = splitter.split_text(job_details)
        for chunk in chunks:
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "job_title": row.get("job_title", ""),
                    "company": row.get("company", ""),
                    "location": row.get("location", ""),
                    "work_arrangement": row.get("work_arrangement", ""),
                    "date_listed": str(row.get("date_listed", "")),
                    "link": row.get("link", ""),
                    "job_details": job_details
                }
            ))
    print(f"✅ Prepared {len(docs)} document chunks from {len(df)} jobs")
    return docs


# === Step 4: Main ===
def main():
    load_dotenv()
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = "jobs"

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

    # Connect to Qdrant client
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    collections = client.get_collections().collections
    existing_collections = [c.name for c in collections]

    if COLLECTION_NAME in existing_collections:
        print(f"📂 Using existing collection: {COLLECTION_NAME}")
        qdrant = Qdrant(
            client=client,
            collection_name=COLLECTION_NAME,
            embeddings=embeddings
        )
    else:
        print(f"🆕 Creating new collection: {COLLECTION_NAME}")
        docs = build_documents_from_csv("data/csv/Python-_jobstreet_2025-09-10.csv")
        qdrant = Qdrant.from_documents(
            docs,
            embeddings,
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            collection_name=COLLECTION_NAME
        )
        
        # Create indexes for filterable metadata fields
        for field in [
            "job_title", "company", "location", "work_arrangement",
            "date_listed", "link", "job_details"
        ]:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_type="keyword"
            )

    # LLM
    llm = ChatOpenAI(
        model="deepseek/deepseek-chat-v3.1:free",
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0
    )

    print("\n🤖 RAG with filters ready! Type 'exit' to quit.\n")

    while True:
        try:
            question = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if question.lower() in {"exit", "quit", ""}:
            print("Bye!")
            break

        filters = parse_query_to_filters(llm, question)
        print(f"🔎 Parsed filters: {filters}")
        qdrant_filter = build_qdrant_filter(filters)

        retriever = qdrant.as_retriever(
            search_kwargs={"k": 10, "filter": qdrant_filter} if qdrant_filter else {"k": 10}
        )
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            return_source_documents=True
        )

        result = qa({"query": question})
        print("\nA:", result.get("result", "No answer"), "\n")

        sources = result.get("source_documents", [])
        if sources:
            print("Sources:")
            for i, doc in enumerate(sources, 1):
                title = doc.metadata.get("job_title", "?")
                company = doc.metadata.get("company", "?")
                location = doc.metadata.get("location", "?")
                print(f"  [{i}] {title} at {company} ({location})")
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()
