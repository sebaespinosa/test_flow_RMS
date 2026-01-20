"""
Interfaces for AI services.
"""

from abc import ABC, abstractmethod
from typing import Any


class IAIExplanationService(ABC):
    """Abstract service for generating AI-powered explanations."""

    @abstractmethod
    async def generate_explanation(self, context: dict[str, Any]) -> dict:
        """
        Generate AI explanation for a match context.

        Args:
            context: Dictionary with invoice, transaction, and scoring data

        Returns:
            Dictionary with keys: explanation (str), confidence (int 0-100)
        """
        raise NotImplementedError
