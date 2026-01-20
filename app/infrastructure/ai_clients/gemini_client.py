"""
Google Gemini API client wrapper with retry and error handling.
"""

import json
import logging
from typing import Optional
import google.genai as genai
from google.api_core.exceptions import (
    ServiceUnavailable,
    TooManyRequests,
    Unauthenticated,
    PermissionDenied,
    InternalServerError,
)

from app.config.settings import Settings
from app.infrastructure.retry import retry_on_exception, RetryError

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Wrapper around Google Generative AI (Gemini) API.
    Handles authentication, context formatting, and response parsing.
    """

    def __init__(self, settings: Settings):
        """
        Initialize Gemini client with API key from settings.
        
        Args:
            settings: Application settings containing GEMINI_API_KEY
            
        Raises:
            ValueError: If API key is missing
        """
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required")

        self.settings = settings
        self.client = genai.Client(api_key=settings.gemini_api_key)
        logger.info(f"Gemini client initialized with model: {settings.gemini_model_id}")

    async def generate_explanation(
        self,
        system_prompt: str,
        context: dict,
        temperature: float = 0.5,
        max_tokens: int = 150,
    ) -> dict:
        """
        Generate AI explanation for invoice-transaction match using Gemini.
        
        Args:
            system_prompt: System instruction for the model
            context: Match context (invoice, transaction, scoring data)
            temperature: Creativity level (0.0-1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Dictionary with keys: explanation (str), confidence (int 0-100)
            
        Raises:
            ValueError: If response is malformed
            Exception: Any transient exceptions (will be caught by retry decorator)
        """
        # Format context into user prompt
        user_prompt = self._format_context(context)

        logger.debug(
            f"Calling Gemini API with model={self.settings.gemini_model_id}, "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )

        try:
            # Call Gemini API (sync call wrapped in async context)
            response = await self._call_gemini_async(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Parse response
            result = self._parse_response(response)
            logger.info("Gemini explanation generated successfully")
            return result

        except (ServiceUnavailable, TooManyRequests, InternalServerError) as e:
            logger.warning(f"Transient Gemini API error: {type(e).__name__}: {str(e)}")
            raise

        except (Unauthenticated, PermissionDenied) as e:
            logger.error(f"Auth error in Gemini API: {type(e).__name__}: {str(e)}")
            raise

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {str(e)}")
            raise ValueError(f"Invalid JSON in Gemini response: {str(e)}") from e

        except Exception as e:
            logger.error(f"Unexpected error calling Gemini API: {type(e).__name__}: {str(e)}")
            raise

    def _format_context(self, context: dict) -> str:
        """
        Format match context into a user prompt for Gemini.
        
        Args:
            context: Dictionary with match data
            
        Returns:
            Formatted prompt string
        """
        return f"""
Please analyze this invoice-transaction match:

INVOICE:
- Amount: {context.get('invoice_amount')} {context.get('invoice_currency')}
- Date: {context.get('invoice_date')}
- Vendor: {context.get('invoice_vendor')}
- Description: {context.get('invoice_description')}

TRANSACTION:
- Amount: {context.get('transaction_amount')} {context.get('transaction_currency')}
- Date: {context.get('transaction_date')}
- Description: {context.get('transaction_description')}

HEURISTIC ANALYSIS:
- Score: {context.get('heuristic_score')}/100
- Reasoning: {context.get('heuristic_reason')}

Provide your expert assessment of this match.
"""

    async def _call_gemini_async(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Call Gemini API (wraps sync call in async context).
        
        Args:
            system_prompt: System instruction
            user_prompt: User message
            temperature: Temperature setting
            max_tokens: Max tokens
            
        Returns:
            Response text
        """
        import asyncio

        def _call_sync() -> str:
            response = self.client.models.generate_content(
                model=self.settings.gemini_model_id,
                contents=[system_prompt, user_prompt],
                config=genai.types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call_sync)

    def _parse_response(self, response_text: str) -> dict:
        """
        Parse Gemini response as JSON with explanation and confidence.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Dictionary with keys: explanation, confidence
            
        Raises:
            ValueError: If response is malformed
        """
        # Try to extract JSON from response (model might wrap it in markdown)
        json_text = response_text.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:]  # Remove ```json
        if json_text.startswith("```"):
            json_text = json_text[3:]  # Remove ```
        if json_text.endswith("```"):
            json_text = json_text[:-3]  # Remove trailing ```

        data = json.loads(json_text.strip())

        # Validate required fields
        if "explanation" not in data:
            raise ValueError("Gemini response missing 'explanation' field")
        if "confidence" not in data:
            raise ValueError("Gemini response missing 'confidence' field")

        # Validate types and ranges
        explanation = str(data["explanation"])
        confidence = int(data["confidence"])

        if not 0 <= confidence <= 100:
            raise ValueError(f"Confidence must be 0-100, got {confidence}")

        return {"explanation": explanation, "confidence": confidence}
