"""
AI-powered explanation service for reconciliation matches.
Wraps LLM calls with retry logic and graceful fallback.
"""

import logging
from typing import Optional
import asyncio

from app.config.settings import Settings
from app.infrastructure.ai_clients.gemini_client import GeminiClient
from app.infrastructure.retry import retry_on_exception, RetryError
from app.ai.interfaces import IAIExplanationService

logger = logging.getLogger(__name__)


class AIExplanationService(IAIExplanationService):
    """
    AI explanation service using Google Gemini.
    Handles retries, timeouts, and graceful degradation.
    """

    def __init__(self, settings: Settings):
        """
        Initialize AI service with Gemini client.
        
        Args:
            settings: Application settings with AI configuration
        """
        self.settings = settings
        self.gemini_client = GeminiClient(settings) if settings.ai_enabled else None
        logger.info(
            f"AIExplanationService initialized (enabled={settings.ai_enabled})"
        )

    async def generate_explanation(self, context: dict) -> dict:
        """
        Generate AI explanation with retry logic.
        
        Args:
            context: Match context (invoice, transaction, scoring)
            
        Returns:
            Dictionary with: explanation (str), confidence (int 0-100)
            
        Raises:
            ValueError: If response is malformed (non-retryable)
        """
        if not self.settings.ai_enabled or not self.gemini_client:
            raise RuntimeError("AI explanation service is disabled")

        return await self._generate_with_retries(context)

    @retry_on_exception(
        max_attempts=3,
        backoff_factor=1.0,
        timeout_seconds=10.0,
        retryable_exceptions=[
            asyncio.TimeoutError,
            TimeoutError,
            # Google API transient errors
            Exception,  # Broad catch that will be filtered below
        ],
        non_retryable_exceptions=[
            ValueError,  # Malformed response
        ],
    )
    async def _generate_with_retries(self, context: dict) -> dict:
        """
        Internal method with retry decorator.
        
        Catches transient errors and retries with exponential backoff.
        Non-retryable errors (auth, malformed) are raised immediately.
        """
        try:
            result = await self.gemini_client.generate_explanation(
                system_prompt=self.settings.ai_system_prompt,
                context=context,
                temperature=self.settings.ai_temperature,
                max_tokens=self.settings.ai_max_tokens,
            )
            return result

        except (ValueError, RuntimeError) as e:
            # Non-retryable errors
            logger.error(f"Non-retryable error in AI service: {type(e).__name__}: {str(e)}")
            raise

        except Exception as e:
            # Let retry decorator handle transient errors
            logger.debug(f"Transient error in AI service (will retry): {type(e).__name__}: {str(e)}")
            raise
