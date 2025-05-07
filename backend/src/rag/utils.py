from fastapi import HTTPException, status
from typing import List, Dict, Any, Optional, Tuple
from openai import AsyncOpenAI
from .config import OPENAI_API_KEY, OPENAI_MODEL, SYSTEM_PROMPT, LIMIT_RETRIEVED_CHUNKS, SIMILARITY_THRESHOLD
from databases import Database
from sentence_transformers import SentenceTransformer
from ..rag.models import RAGResponse
import logging
import json

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def retrieve_relevant_chunks(
    db: Database,
    query_embedding: List[float],
    object_keys: List[str],
) -> List[Dict[str, Any]]:
    """Tool to retrieve relevant chunks based on query embedding."""
    chunks = await search_similar_chunks_by_objects(
        db=db,
        query_embedding=query_embedding,
        object_keys=object_keys,
    )
    return chunks

def get_retrieval_tool_description() -> Dict[str, Any]:
    """Get the description of the retrieval tool for the LLM."""
    return {
        "type": "function",
        "function": {
            "name": "retrieve_context",
            "description": "Retrieve relevant context from the knowledge base to help answer the user's query",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation of why retrieval is necessary for this query"
                    }
                },
                "required": ["reasoning"]
            }
        }
    }




async def create_rag_response(
    db: Database,
    query: str,
    object_keys: List[str],
    model_path: str,
) -> Tuple[str, List[str]]:
    """
    Creates a response using the LLM, which can optionally retrieve context.
    """
    messages = [
        {
            "role": "system", 
            "content": SYSTEM_PROMPT + "\nYou have access to a knowledge base. Before answering, decide if you need to retrieve relevant context."},
        {
            "role": "user", 
            "content": query
        }
    ]

    sources = []

    try:
        logger.info(" Calling OpenAI to decide if context is needed...")
        decision_response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=[get_retrieval_tool_description()],
            tool_choice="auto"
        )
        
        first_message = decision_response.choices[0].message
        logger.info(f" OpenAI decision: {first_message.tool_calls}")

        if first_message.tool_calls:
            logger.info(" Embedding user query and retrieving chunks...")
            query_embedding = await embed_user_query(query, model_path=model_path)

            chunks = await retrieve_relevant_chunks(
                db=db,
                query_embedding=query_embedding,
                object_keys=object_keys,
            )

            logger.info(f"Retrieved {len(chunks)} chunks")
            if chunks:
                logger.debug(f"Top chunk preview: {chunks[0]['text'][:100]}...")

            context = "\n\n".join([chunk["text"] for chunk in chunks])
            for chunk in chunks:
                # get original file name from object key
                file_name = await db.fetch_one(
                    query="SELECT original_filename FROM user_files WHERE object_key = :object_key",
                    values={"object_key": chunk["object_key"]}
                )

                sources.append({
                    "object_key": chunk["object_key"],
                    "file_name": file_name["original_filename"],
                    "text": chunk["text"]
                })

            messages.append({
                "role": "system",
                "content": f"""Here is the relevant context:
                ---------------------
                {context}
                ---------------------
                Use this context to answer the user's query. 
                If the answer cannot be found in the context, do not answer the question. Instead, apologize and say that you did not find an answer in the context."""
            })

        logger.info("Generating final response from OpenAI...")
        final_response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
        )

        result = final_response.choices[0].message.content
        logger.info(f"Final response: {result[:100]}...")

        return result, sources

    except Exception as e:
        logger.exception(f"Error in create_rag_response: {str(e)}")
        return f"Error generating response: {str(e)}", []


async def embed_user_query(
    query: str,
    model_path: str
) -> List[float]:
    """
    Embed a user query using a given model.
    """
    # Load the model
    model = SentenceTransformer(model_path)
    
    # Generate embedding
    query_embedding = model.encode(query).tolist()
    return query_embedding


async def search_similar_chunks_by_objects(
    db: Database,
    query_embedding: List[float],
    object_keys: List[str],
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    logger.info(f"Searching for similar chunks by objects: {object_keys}")
    try:
        query = """
        SELECT 
            text,
            object_key,
            1 - (embedding <=> :query_embedding) AS similarity
        FROM embeddings
        WHERE 
            object_key = ANY(:object_keys)
            AND 1 - (embedding <=> :query_embedding) > :threshold
        ORDER BY similarity DESC
        LIMIT :limit
        """
        values = {
            "query_embedding": f"[{', '.join(map(str, query_embedding))}]",  # 🛠️ format for pgvector
            "object_keys": object_keys,
            "threshold": similarity_threshold,
            "limit": limit,
        }

        results = await db.fetch_all(query, values)

        return [
            {
                "text": row["text"],
                "object_key": row["object_key"],
                "similarity": float(row["similarity"]),
            }
            for row in results
        ]

    except Exception as error:
        logger.error(f"Error performing semantic search: {error}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error))