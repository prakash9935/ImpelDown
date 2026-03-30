"""
LLM API Client (US-405, Sprint 3)

Calls Groq (default) or Azure OpenAI with temperature=0.0 for deterministic responses.

Implements:
  - Groq Llama-3.2 integration (fast, cheap)
  - Azure OpenAI fallback (enterprise SLA)
  - Temperature=0.0 for determinism
  - Error handling for rate limits, timeouts
"""

import logging

logger = logging.getLogger(__name__)


async def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    """
    Call LLM with temperature=0.0 for deterministic responses (US-405).

    Attempts Groq first (fast, cheap), then Azure OpenAI if configured.
    Raises ValueError if no provider is configured.

    Args:
        prompt: Full prompt with context + query
        max_tokens: Max response length (default 1024)

    Returns:
        LLM response text

    Raises:
        ValueError: If no LLM provider is configured
    """
    from src.secrag.config import settings

    # Try Groq
    if settings.groq_api_key:
        try:
            from langchain_groq import ChatGroq

            client = ChatGroq(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
                temperature=0.0,
                max_tokens=max_tokens,
            )

            response = await client.ainvoke(prompt)
            logger.info(
                f"LLM response via Groq ({settings.groq_model}): {len(response.content)} chars"
            )
            return response.content

        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise

    # Try Azure OpenAI
    elif settings.azure_openai_api_key and settings.azure_openai_endpoint:
        try:
            from langchain_openai import AzureChatOpenAI

            client = AzureChatOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                deployment_name=settings.azure_openai_deployment_name,
                temperature=0.0,
                max_tokens=max_tokens,
            )

            response = await client.ainvoke(prompt)
            logger.info(
                f"LLM response via Azure OpenAI ({settings.azure_openai_deployment_name}): {len(response.content)} chars"  # noqa: E501
            )
            return response.content

        except Exception as e:
            logger.error(f"Azure OpenAI API call failed: {e}")
            raise

    else:
        raise ValueError(
            "No LLM provider configured. Set GROQ_API_KEY or Azure credentials "
            "(AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME)"
        )
