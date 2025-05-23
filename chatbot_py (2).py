import numpy as np


import langchain
print(langchain.__version__)

!pip install langchain_chroma

!pip install langchain_openai

!pip install langchain_community

!pip install pypdf

import os
os.environ["openai_api_key"] = "api-key"

from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini",openai_api_key="api-key")
    llm_response = llm.invoke("Tell me a joke")
    print(llm_response)

from langchain_core.output_parsers import StrOutputParser

    output_parser = StrOutputParser()
    chain = llm | output_parser
    result = chain.invoke("Tell me a joke")
    print(result)

from typing import List
    from pydantic import BaseModel, Field

    class MobileReview(BaseModel):
        phone_model: str = Field(description="Name and model of the phone")
        rating: float = Field(description="Overall rating out of 5")
        pros: List[str] = Field(description="List of positive aspects")
        cons: List[str] = Field(description="List of negative aspects")
        summary: str = Field(description="Brief summary of the review")

    review_text = """
    Just got my hands on the new Galaxy S21 and wow, this thing is slick! The screen is gorgeous,
    colors pop like crazy. Camera's insane too, especially at night - my Insta game's never been
    stronger. Battery life's solid, lasts me all day no problem.
    Not gonna lie though, it's pretty pricey. And what's with ditching the charger? C'mon Samsung.
    Also, still getting used to the new button layout, keep hitting Bixby by mistake.
    Overall, I'd say it's a solid 4 out of 5. Great phone, but a few annoying quirks keep it from
    being perfect. If you're due for an upgrade, definitely worth checking out!
    """

    structured_llm = llm.with_structured_output(MobileReview)
    output = structured_llm.invoke(review_text)
    print(output)
    print(output.pros)

from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_template("Tell me a short joke about {topic}")
    chain = prompt | llm | output_parser
    result = chain.invoke({"topic": "programming"})
    print(result)

from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content="You are a helpful assistant that tells jokes."),
        HumanMessage(content="Tell me about programming")
    ]
    response = llm.invoke(messages)
    print(response)

    template = ChatPromptTemplate([
        ("system", "You are a helpful assistant that tells jokes."),
        ("human", "Tell me about {topic}")
    ])
    chain = template | llm
    response = chain.invoke({"topic": "programming"})
    print(response)

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document
import os

def load_documents(folder_path: str) -> List[Document]:
    documents = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif filename.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        else:
            print(f"Unsupported file type: {filename}")
            continue
        documents.extend(loader.load())
    return documents

folder_path = "/content/chatbot_file"
documents = load_documents(folder_path)
print(f"Loaded {len(documents)} documents from the folder.")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)

splits = text_splitter.split_documents(documents)
print(f"Split the documents into {len(splits)} chunks.")

print(documents[0])

print(splits[1])

print(splits[0].metadata)

from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(openai_api_key="your_api_key")
document_embeddings = embeddings.embed_documents([split.page_content for split in splits])
print(f"Created embeddings for {len(document_embeddings)} document chunks.")

from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings

embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
document_embeddings = embedding_function.embed_documents([split.page_content for split in splits])
print(document_embeddings[0][:5])  # Printing first 5 elements of the first embedding

from langchain_chroma import Chroma

collection_name = "my_collection"
vectorstore = Chroma.from_documents(
    collection_name=collection_name,
    documents=splits,
    embedding=embedding_function,
    persist_directory="./chroma_db"
)
print("Vector store created and persisted to './chroma_db'")

query = "When was GreenGrow Innovations founded?"
search_results = vectorstore.similarity_search(query, k=2)
print(f"\nTop 2 most relevant chunks for the query: '{query}'\n")
for i, result in enumerate(search_results, 1):
    print(f"Result {i}:")
    print(f"Source: {result.metadata.get('source', 'Unknown')}")
    print(f"Content: {result.page_content}")
    print()

retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
retriever_results = retriever.invoke("When was GreenGrow Innovations founded?")
print(retriever_results)

from langchain_core.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

template = """Answer the question based only on the following context:
{context}
Question: {question}
Answer: """

prompt = ChatPromptTemplate.from_template(template)

def docs2str(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | docs2str, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

question = "When did technova achieved unicorn status?"
response = rag_chain.invoke(question)
print(f"Question: {question}")
print(f"Answer: {response}")

from langchain_core.prompts import MessagesPlaceholder
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain

contextualize_q_system_prompt = """
Given a chat history and the latest user question
which might reference context in the chat history,
formulate a standalone question which can be understood
without the chat history. Do NOT answer the question,
just reformulate it if needed and otherwise return it as is.
"""

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

contextualize_chain = contextualize_q_prompt | llm | StrOutputParser()
print(contextualize_chain.invoke({"input": "Where is it headquartered?", "chat_history": []}))

from langchain.chains import create_retrieval_chain

history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
)

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant. Use the following context to answer the user's question."),
    ("system", "Context: {context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

from langchain_core.messages import HumanMessage, AIMessage

chat_history = []
question1 = "When was technova Innovations founded?"
answer1 = rag_chain.invoke({"input": question1, "chat_history": chat_history})['answer']
chat_history.extend([
    HumanMessage(content=question1),
    AIMessage(content=answer1)
])

print(f"Human: {question1}")
print(f"AI: {answer1}\n")

question2 = "When did it launch first ai based assistant?"
answer2 = rag_chain.invoke({"input": question2, "chat_history": chat_history})['answer']
chat_history.extend([
    HumanMessage(content=question2),
    AIMessage(content=answer2)
])

print(f"Human: {question2}")
print(f"AI: {answer2}")

import sqlite3
from datetime import datetime
import uuid

DB_NAME = "rag_app.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_application_logs():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS application_logs
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_query TEXT,
    gpt_response TEXT,
    model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()

def insert_application_logs(session_id, user_query, gpt_response, model):
    conn = get_db_connection()
    conn.execute('INSERT INTO application_logs (session_id, user_query, gpt_response, model) VALUES (?, ?, ?, ?)',
                 (session_id, user_query, gpt_response, model))
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_query, gpt_response FROM application_logs WHERE session_id = ? ORDER BY created_at', (session_id,))
    messages = []
    for row in cursor.fetchall():
        messages.extend([
            {"role": "human", "content": row['user_query']},
            {"role": "ai", "content": row['gpt_response']}
        ])
    conn.close()
    return messages

# Initialize the database
create_application_logs()

# Example usage for a new user
session_id = str(uuid.uuid4())
question = "What is technova?"
chat_history = get_chat_history(session_id)
answer = rag_chain.invoke({"input": question, "chat_history": chat_history})['answer']
insert_application_logs(session_id, question, answer, "gpt-3.5-turbo")
print(f"Human: {question}")
print(f"AI: {answer}\n")

# Example of a follow-up question
question2 = "What is their ai baesd asisstant?"
chat_history = get_chat_history(session_id)
answer2 = rag_chain.invoke({"input": question2, "chat_history": chat_history})['answer']
insert_application_logs(session_id, question2, answer2, "gpt-3.5-turbo")
print(f"Human: {question2}")
print(f"AI: {answer2}")
