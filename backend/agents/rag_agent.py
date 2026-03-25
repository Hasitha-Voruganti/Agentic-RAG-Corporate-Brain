"""
agents/rag_agent.py — Agentic RAG using Groq with Redis caching
"""
import json
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from groq import AsyncGroq
from loguru import logger

from core.config import get_settings
from retrieval.hybrid import hybrid_retriever, RetrievedChunk

settings = get_settings()
client = AsyncGroq(api_key=settings.groq_api_key)


@dataclass
class AgentState:
    original_query: str
    user_roles: list[str]
    current_query: str = ""
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    answer: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    iterations: int = 0
    is_complete: bool = False
    rewrite_history: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.current_query = self.original_query


class RAGAgent:

    async def _get_redis(self):
        """Get Redis client lazily."""
        try:
            import redis.asyncio as redis
            return redis.from_url(settings.redis_url)
        except Exception:
            return None

    def _cache_key(self, query: str, user_roles: list[str]) -> str:
        """Generate unique cache key for query + roles."""
        content = query.lower().strip() + str(sorted(user_roles))
        return f"rag_cache:{hashlib.md5(content.encode()).hexdigest()}"

    async def _get_cached(
        self, query: str, user_roles: list[str]
    ) -> Optional[dict]:
        """Try to get a cached result from Redis."""
        try:
            r = await self._get_redis()
            if not r:
                return None
            cached = await r.get(self._cache_key(query, user_roles))
            if cached:
                logger.info(f"Cache hit for: {query[:50]}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        return None

    async def _set_cached(
        self, query: str, user_roles: list[str], data: dict
    ):
        """Save result to Redis cache for 1 hour."""
        try:
            r = await self._get_redis()
            if not r:
                return
            await r.setex(
                self._cache_key(query, user_roles),
                3600,
                json.dumps(data)
            )
            logger.info("Query result cached for 1 hour")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    async def run(self, query: str, user_roles: list[str]) -> AgentState:
        # Check Redis cache first — return instantly if found
        cached = await self._get_cached(query, user_roles)
        if cached:
            state = AgentState(
                original_query=query,
                user_roles=user_roles,
                answer=cached["answer"],
                confidence=cached["confidence"],
                reasoning=cached["reasoning"],
                iterations=cached["iterations"],
                rewrite_history=cached.get("rewrite_history", []),
                is_complete=True
            )
            return state

        # Run full agent pipeline
        state = AgentState(original_query=query, user_roles=user_roles)
        logger.info(f"Agent starting for query: {query[:80]}...")

        for iteration in range(settings.max_agent_iterations):
            state.iterations = iteration + 1
            logger.info(f"Agent iteration {state.iterations}")

            # PLAN
            plan = await self._plan(state)
            if plan.get("action") == "rewrite":
                new_q = plan.get("rewritten_query", state.current_query)
                state.rewrite_history.append(state.current_query)
                state.current_query = new_q
                logger.info(f"Query rewritten to: {new_q}")

            # ACT
            state.retrieved_chunks = await hybrid_retriever.search(
                query=state.current_query,
                user_roles=state.user_roles,
                top_k=settings.top_k_rerank
            )
            logger.info(f"Retrieved {len(state.retrieved_chunks)} chunks")

            if not state.retrieved_chunks:
                state.answer = (
                    "I could not find relevant information in the "
                    "knowledge base for your query. Please try rephrasing "
                    "or upload relevant documents first."
                )
                state.confidence = 0.0
                state.is_complete = True
                break

            # VERIFY
            verify_result = await self._verify(state)
            state.answer = verify_result["answer"]
            state.confidence = verify_result["confidence"]
            state.reasoning = verify_result["reasoning"]

            if (
                verify_result["confidence"]
                >= settings.self_reflection_threshold
            ):
                state.is_complete = True
                logger.info(
                    f"Answer accepted "
                    f"(confidence={state.confidence:.2f})"
                )
                break
            else:
                logger.info(
                    f"Low confidence ({state.confidence:.2f}), "
                    f"retrying..."
                )

        if not state.is_complete:
            state.is_complete = True

        # Cache result for future identical queries
        await self._set_cached(query, user_roles, {
            "answer": state.answer,
            "confidence": state.confidence,
            "reasoning": state.reasoning,
            "iterations": state.iterations,
            "rewrite_history": state.rewrite_history
        })

        return state

    async def _plan(self, state: AgentState) -> dict:
        """Decide: answer directly OR rewrite the query first."""
        system = """You are a query analysis expert for a corporate knowledge base.
Analyze the query and decide the best action:
- "answer": query is clear enough, proceed with retrieval
- "rewrite": query is too vague, ambiguous, or uses abbreviations

Common abbreviations to expand:
- wfh → work from home policy
- pf → provident fund
- ctc → cost to company salary structure
- posh → prevention of sexual harassment policy
- esop → employee stock options
- l&d → learning and development
- hmo → health maintenance organization
- tds → tax deducted at source

Respond ONLY with valid JSON:
{"action": "answer", "rewritten_query": "...", "reasoning": "..."}"""

        history_text = ""
        if state.rewrite_history:
            history_text = (
                f"\nPrevious query versions tried: {state.rewrite_history}"
            )

        try:
            resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": (
                            f"Query: {state.current_query}{history_text}"
                        )
                    }
                ],
                temperature=0.1,
                max_tokens=200
            )
            content = resp.choices[0].message.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except Exception as e:
            logger.warning(f"Plan step failed: {e}")

        return {
            "action": "answer",
            "rewritten_query": state.current_query,
            "reasoning": ""
        }

    async def _verify(self, state: AgentState) -> dict:
        """Generate answer from context then self-reflect on quality."""
        context_text = self._format_context(state.retrieved_chunks)

        answer_system = answer_system = """You are a helpful corporate knowledge assistant.
Answer questions clearly and naturally like a knowledgeable colleague would.

Follow this response structure but do NOT include any section headers or
numbers like "1." or "2." anywhere in your response:

First give the direct answer in 1-3 clear sentences.
Never start with "According to..." or "It is mentioned that..."
Bold important numbers, dates, and key terms using **bold**.

Then if there are multiple details worth listing, use bullet points.
Use bold for key figures like **20 days**, **6 months**, **₹50,000**.

Always end your response with this exact source citation block:

---
📄 Source: [Exact Document Title] — [Section Name]
   └ [One sentence describing what this section covers]

If multiple documents contributed:
📄 Source 1: [Document Title] — [Section Name]
   └ [One sentence description]
📄 Source 2: [Document Title] — [Section Name]
   └ [One sentence description]

STRICT RULES — follow without exception:
- Do NOT write headers like "DIRECT ANSWER", "DETAILS", "SOURCE CITATION"
- Do NOT number sections like "1.", "2.", "3."
- Always give direct answer FIRST before any bullet points
- Never reference documents as "Document 1" or "Document 2"
- Never say "it is mentioned that" or "as per the document"
- Always end with the source citation block — never skip it
- Use the exact section name from the context if visible
- If the question asks about something completely absent from the context
  such as customer refunds, stock prices, external policies, or anything
  not covered in the uploaded documents — respond with exactly this:
  "This information is not available in the company knowledge base.
   You may want to contact the relevant department directly."
  Do NOT try to find loosely related content as a substitute.
- A confident "not found" is always better than a loosely related answer
- Do not repeat the same information twice"""

        try:
            answer_resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": answer_system},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {state.current_query}\n\n"
                            f"Context from knowledge base:\n{context_text}"
                        )
                    }
                ],
                temperature=0.2,
                max_tokens=1200
            )
            answer = answer_resp.choices[0].message.content

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return {
                "answer": "Failed to generate answer. Please try again.",
                "confidence": 0.0,
                "reasoning": str(e)
            }

        # Self-reflection — assess answer quality
        reflection_system = """You are a quality assessor for AI-generated answers.

Rate confidence from 0.0 to 1.0 based on these rules:
- 0.85 to 0.95: Answer directly addresses the question with specific facts from context
- 0.70 to 0.84: Answer is mostly correct but may be missing some details
- 0.50 to 0.69: Answer is vague or only partially addresses the question
- 0.0 to 0.49: Answer is wrong, hallucinated, or completely off-topic

Give 0.85+ if:
- The answer contains specific numbers, dates, or names from the context
- The answer directly answers what was asked
- The source citation is present

Give 0.0 if:
- The answer is clearly made up and not in the context
- The answer is about a completely different topic

Respond ONLY with valid JSON:
{
  "confidence": 0.85,
  "reasoning": "brief explanation",
  "is_hallucinated": false
}"""

        try:
            reflection_resp = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": reflection_system},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {state.current_query}\n\n"
                            f"Generated Answer:\n{answer}\n\n"
                            f"Context chunks available: "
                            f"{len(state.retrieved_chunks)}"
                        )
                    }
                ],
                temperature=0.1,
                max_tokens=150
            )
            content = reflection_resp.choices[0].message.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                reflection = json.loads(content[start:end])
            else:
                reflection = {
                    "confidence": 0.7,
                    "reasoning": "Unable to parse reflection",
                    "is_hallucinated": False
                }

        except Exception as e:
            logger.warning(f"Reflection failed: {e}")
            reflection = {
                "confidence": 0.7,
                "reasoning": "Reflection unavailable",
                "is_hallucinated": False
            }

        # Reject hallucinated answers
        if reflection.get("is_hallucinated"):
            logger.warning("Hallucination detected — rejecting answer")
            answer = (
                "I was unable to find a well-grounded answer in the "
                "available documents. Please try rephrasing your question."
            )
            reflection["confidence"] = 0.0

        return {
            "answer": answer,
            "confidence": float(reflection.get("confidence", 0.7)),
            "reasoning": reflection.get("reasoning", ""),
        }

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        """
        Format retrieved chunks into structured context for the LLM.
        Includes document title, page number, and chunk type so the
        LLM can produce accurate source citations.
        """
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            doc_title = chunk.title or chunk.filename

            location = ""
            if chunk.page_num:
                if chunk.chunk_type == "table":
                    location = f"Table on page {chunk.page_num}"
                elif chunk.chunk_type == "image_ocr":
                    location = f"Scanned page {chunk.page_num}"
                else:
                    location = f"Page {chunk.page_num}"

            source_line = f"Document: {doc_title}"
            if location:
                source_line += f" | {location}"

            parts.append(
                f"[{source_line}]\n{chunk.content}"
            )

        return "\n\n---\n\n".join(parts)


# This line is what main.py imports — must be at the bottom
rag_agent = RAGAgent()