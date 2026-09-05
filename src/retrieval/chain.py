"""RAG chain: retrieve context from the vector store, generate answer via LLM.

Supports two providers (set LLM_PROVIDER in .env):
  - openrouter  → any model on OpenRouter (free or paid), OpenAI-compatible
  - anthropic   → direct Anthropic API (Claude)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import LLMProvider, settings
from src.retrieval.vectorstore import search

SYSTEM_PROMPT = """\
You are an SRE assistant that resolves production incidents.  You answer
questions using ONLY the retrieved incident context below.  For every claim,
cite the source file in brackets, e.g. [inc-003-node-pressure.md].

If the context does not contain enough information, say so — do not guess.

When recommending actions, list them in order of priority and flag any that
are destructive (e.g. pod deletion, node drain).

IMPORTANT: Respond with ONLY the final answer. Do NOT include any thinking,
reasoning process, analysis steps, or chain-of-thought. Be direct and concise.

## Retrieved Incident Context
{context}
"""

USER_TEMPLATE = "{question}"


@dataclass
class QueryResult:
    answer: str
    sources: list[Document] = field(default_factory=list)


def _build_llm() -> BaseChatModel:
    """Instantiate the right LangChain chat model based on config."""
    if settings.llm_provider == LLMProvider.OPENROUTER:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openrouter_model,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base=settings.openrouter_base_url,
            max_tokens=settings.llm_max_tokens,
            default_headers={
                "HTTP-Referer": "https://github.com/incident-rag-engine",
                "X-Title": "Incident RAG Engine",
            },
        )

    # Anthropic direct
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        max_tokens=settings.llm_max_tokens,
    )


def _format_context(docs: list[Document]) -> str:
    sections: list[str] = []
    for i, doc in enumerate(docs, 1):
        src = doc.metadata.get("source", "unknown")
        severity = doc.metadata.get("severity", "")
        header = f"[{i}] source={src}"
        if severity:
            header += f"  severity={severity}"
        sections.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(sections)


def build_chain() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", USER_TEMPLATE),
        ]
    )


def query(question: str, k: int = 5) -> QueryResult:
    """End-to-end RAG: retrieve chunks → build prompt → call LLM."""
    docs = search(question, k=k)
    if not docs:
        return QueryResult(
            answer="No relevant incidents found in the knowledge base."
        )

    context = _format_context(docs)
    prompt = build_chain()
    llm = _build_llm()

    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})
    return QueryResult(answer=answer, sources=docs)
