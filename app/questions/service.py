import asyncio
import logging
import os
import tempfile
from uuid import UUID, uuid4

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models import Answer, Interview, Question, Session
from app.ai.generator import generate_questions as llm_generate

logger = logging.getLogger(__name__)

# Strong references — prevents background tasks from being GC'd before completion.
_background_tasks: set[asyncio.Task] = set()


async def _index_and_generate_background(
    interview_id: UUID,
    text_content: str | None,
    file_paths: list[str],
    count: int,
    topic: str | None,
) -> None:
    from app.db.session import async_session_factory

    try:
        if text_content:
            await load_and_index_questions(text_content, interview_id)

        for file_path in file_paths:
            try:
                await load_and_index_file(file_path, interview_id)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        async with async_session_factory() as db:
            interview = await db.get(Interview, interview_id)
            if interview:
                await generate_and_save_questions(
                    db=db,
                    interview_id=interview_id,
                    role=interview.role,
                    difficulty=interview.difficulty,
                    count=count,
                    topic=topic,
                )
    except Exception:
        logger.exception("Background index+generate failed for interview %s", interview_id)


def schedule_generation(
    interview_id: UUID,
    count: int = 5,
    topic: str | None = None,
    text_content: str | None = None,
    file_paths: list[str] | None = None,
) -> None:
    task = asyncio.create_task(
        _index_and_generate_background(interview_id, text_content, file_paths or [], count, topic)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def load_and_index_file(file_path: str, interview_id: UUID) -> list[str]:
    """
    Loads a file (PDF or TXT), chunks it, and indexes it in the vector store only.
    Nothing is written to the relational DB — the vector store is the sole home
    for RAG source material.
    """
    if file_path.lower().endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path)

    documents = loader.load()

    if file_path.lower().endswith((".md", ".markdown")):
        from langchain_text_splitters import Language
        text_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN,
            chunk_size=1000,
            chunk_overlap=100,
        )
    else:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
        )
    chunks = text_splitter.split_documents(documents)

    for chunk in chunks:
        chunk.metadata["interview_id"] = str(interview_id)
        if "id" not in chunk.metadata:
            chunk.metadata["id"] = str(uuid4())

    return await asyncio.to_thread(
        settings.lang_chain.vector_store.add_documents,
        chunks,
        ids=[c.metadata["id"] for c in chunks],
    )


async def load_and_index_questions(text_content: str, interview_id: UUID) -> list[str]:
    """
    Chunks plain text and indexes it in the vector store only.
    """
    from langchain_text_splitters import Language
    text_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.MARKDOWN,
        chunk_size=1000,
        chunk_overlap=100,
    )
    chunks = text_splitter.split_text(text_content)

    documents = [
        Document(
            page_content=chunk,
            metadata={"interview_id": str(interview_id), "id": str(uuid4())},
        )
        for chunk in chunks
    ]

    return await asyncio.to_thread(
        settings.lang_chain.vector_store.add_documents,
        documents,
        ids=[d.metadata["id"] for d in documents],
    )


async def search_questions(
    db: AsyncSession,
    query: str | None,
    interview_id: UUID,
    k: int = 5,
) -> list[Document]:
    """
    Semantic search when query is provided; raw fetch from the vector store
    backing table when it is not.
    """
    if query:
        filter_dict = {"interview_id": str(interview_id)}
        docs_with_scores = await asyncio.to_thread(
            settings.lang_chain.vector_store.similarity_search_with_score,
            query,
            k=k,
            filter=filter_dict,
        )
        results = []
        for doc, score in docs_with_scores:
            if score < 0.9:
                doc.metadata["score"] = score
                results.append(doc)
        return results

    # No query — fetch raw chunks from the vector store's backing table.
    rows = (
        await db.execute(
            text(
                """
                SELECT e.id::text, e.document, e.cmetadata
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection
                  AND e.cmetadata->>'interview_id' = :interview_id
                LIMIT :k
                """
            ),
            {
                "collection": settings.lang_chain.collection_name,
                "interview_id": str(interview_id),
                "k": k,
            },
        )
    ).fetchall()

    return [
        Document(
            page_content=row[1],
            metadata={"interview_id": str(interview_id), "id": row[0], **(row[2] or {})},
        )
        for row in rows
    ]


async def get_question(question_id: str) -> Document | None:
    docs = await asyncio.to_thread(
        settings.lang_chain.vector_store.get_by_ids,
        [question_id],
    )
    return docs[0] if docs else None


async def delete_question(question_id: str) -> bool:
    """
    Deletes a chunk from the vector store.
    Returns False when the chunk does not exist.
    """
    docs = await asyncio.to_thread(
        settings.lang_chain.vector_store.get_by_ids,
        [question_id],
    )
    if not docs:
        return False
    await asyncio.to_thread(settings.lang_chain.vector_store.delete, [question_id])
    return True


async def generate_and_save_questions(
    db: AsyncSession,
    interview_id: UUID,
    role: str | None,
    difficulty: str | None,
    count: int = 5,
    topic: str | None = None,
) -> list[Question]:
    """
    Generate interview questions with the LLM using RAG context from the vector
    store, then persist them in the relational DB so sessions can serve them.
    Raises on LLM or parsing failure.
    """

    # Use topic as the search query when available — it's the most specific signal.
    # Fall back to role so semantic search still filters by relevance across multiple
    # documents. Only fetch all chunks unfiltered when neither is set.
    query = topic or role
    docs = await search_questions(db, query, interview_id, k=10)
    context_chunks = [doc.page_content for doc in docs]

    interview = await db.get(Interview, interview_id)
    interview_type = interview.interview_type if interview else "behavioral"

    generated = await llm_generate(
        context_chunks=context_chunks,
        role=role,
        difficulty=difficulty,
        topic=topic,
        count=count,
        interview_type=interview_type,
    )

    saved: list[Question] = []
    for i, q_data in enumerate(generated):
        question = Question(
            interview_id=interview_id,
            text=q_data["text"],
            category=q_data.get("category"),
            difficulty=q_data.get("difficulty"),
            question_type=q_data.get("question_type", interview_type),
            starter_code=q_data.get("starter_code"),
            examples=q_data.get("examples"),
            order=i,
        )
        db.add(question)
        saved.append(question)

    await db.commit()
    for q in saved:
        await db.refresh(q)

    return saved


async def delete_all_interview_questions(db: AsyncSession, interview_id: UUID) -> bool:
    """
    Removes all vector store chunks for the interview, then lets the DB cascade
    handle the generated questions in the questions table.
    """
    rows = (
        await db.execute(
            text(
                """
                SELECT e.id::text
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection
                  AND e.cmetadata->>'interview_id' = :interview_id
                """
            ),
            {
                "collection": settings.lang_chain.collection_name,
                "interview_id": str(interview_id),
            },
        )
    ).fetchall()

    ids = [row[0] for row in rows]
    if ids:
        await asyncio.to_thread(settings.lang_chain.vector_store.delete, ids)

    return True


async def list_questions(db: AsyncSession, interview_id: UUID) -> list[Question]:
    """Return all generated questions for an interview, ordered by their position."""
    from sqlalchemy import select

    result = await db.execute(
        select(Question)
        .where(Question.interview_id == interview_id)
        .order_by(Question.order, Question.created_at)
    )
    return list(result.scalars().all())


async def reset_interview_questions(db: AsyncSession, interview_id: UUID) -> None:
    """Set all questions for an interview back to 'active' status."""
    from sqlalchemy import update
    from app.db.models import Interview
    
    await db.execute(
        update(Question)
        .where(Question.interview_id == interview_id)
        .values(status="active")
    )
    
    await db.execute(
        update(Interview)
        .where(Interview.id == interview_id)
        .values(status="active")
    )
    
    await db.commit()


async def delete_question_by_id(
    db: AsyncSession, question_id: UUID, interview_id: UUID
) -> bool:
    """
    Delete a question from the SQL table and any matching vector-store chunks.

    Chunk matching is done by exact document text + interview_id, since there is
    no stored FK between the questions table and langchain_pg_embedding.
    Returns False when the question does not exist or belongs to a different interview.
    """
    from sqlalchemy import delete
    
    try:
        # Get question text first for vector store cleanup
        q_res = await db.execute(select(Question).where(Question.id == question_id))
        question = q_res.scalar_one_or_none()
        if not question or question.interview_id != interview_id:
            logger.warning(f"Question {question_id} not found for interview {interview_id}")
            return False
            
        question_text = question.text
        
        # Atomic delete
        stmt = delete(Question).where(Question.id == question_id, Question.interview_id == interview_id)
        result = await db.execute(stmt)
        await db.commit()
        
        if result.rowcount == 0:
            logger.warning(f"No rows deleted for question {question_id}")
            return False
            
        logger.info(f"Successfully deleted question {question_id} from SQL")
    except Exception as e:
        logger.error(f"SQL delete failed for question {question_id}: {e}")
        await db.rollback()
        return False

    try:
        # Find and remove any vector-store chunks whose text matches the question.
        res = await db.execute(
            text(
                """
                SELECT e.id::text
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection
                  AND e.cmetadata->>'interview_id' = :interview_id
                  AND e.document = :question_text
                """
            ),
            {
                "collection": settings.lang_chain.collection_name,
                "interview_id": str(interview_id),
                "question_text": question_text,
            },
        )
        rows = res.fetchall()
        chunk_ids = [row[0] for row in rows]
        
        if chunk_ids:
            logger.info("Deleting %d vector chunks for question %s", len(chunk_ids), question_id)
            await asyncio.to_thread(settings.lang_chain.vector_store.delete, chunk_ids)
    except Exception as e:
        logger.warning("Failed to delete vector chunks for question %s: %s", question_id, e)
        # We don't return False here because the SQL deletion was already successful

    return True


async def get_next_question(db: AsyncSession, session: Session) -> Question | None:
    """
    Returns a random active question for the session's interview that has not
    been answered yet in this session. Returns None when all questions are exhausted.
    """
    from sqlalchemy import select, func

    # 1. Identify questions already answered in this session
    answered_stmt = select(Answer.question_id).where(Answer.session_id == session.id)
    answered_ids = (await db.execute(answered_stmt)).scalars().all()

    # 2. Select a random active question that isn't in the answered list
    query = (
        select(Question)
        .where(
            Question.interview_id == session.interview_id,
            Question.status == "active"
        )
    )
    
    if answered_ids:
        query = query.where(Question.id.notin_(answered_ids))

    result = await db.execute(query.order_by(Question.order).limit(1))
    return result.scalar_one_or_none()
