"""
LLM integration for conversation analysis.
"""
import logging
import json
import os
from typing import Dict, List, Any, Optional, Union, Tuple

import litellm
from litellm import completion

from devjourney.config.settings import config
from devjourney.utils.credentials import get_claude_api_key, get_openai_api_key

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """LLM-based analyzer for conversations."""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the LLM analyzer.
        
        Args:
            provider: LLM provider (ollama, claude, openai)
            model: Model to use for analysis
        """
        self.provider = provider or config.llm.provider
        self.model = model or config.llm.model
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.fallback_providers = config.llm.fallback_providers
        
        # Set up API keys
        self._setup_api_keys()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized LLM analyzer with provider: {self.provider}, model: {self.model}")
    
    def _setup_api_keys(self) -> None:
        """Set up API keys for different providers."""
        # Claude API key
        claude_api_key = get_claude_api_key()
        if claude_api_key:
            os.environ["ANTHROPIC_API_KEY"] = claude_api_key
        
        # OpenAI API key
        openai_api_key = get_openai_api_key()
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
    
    def analyze(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[bool, str]:
        """
        Analyze text using the configured LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            system_prompt: Optional system prompt
            
        Returns:
            Tuple of (success, response)
        """
        # Try the primary provider first
        success, response = self._try_provider(self.provider, self.model, prompt, system_prompt)
        if success:
            return success, response
        
        # Try fallback providers
        for provider in self.fallback_providers:
            if provider == self.provider:
                continue  # Skip if it's the same as the primary provider
            
            # Get appropriate model for the fallback provider
            fallback_model = self._get_fallback_model(provider)
            if not fallback_model:
                continue
            
            self.logger.info(f"Trying fallback provider: {provider} with model: {fallback_model}")
            success, response = self._try_provider(provider, fallback_model, prompt, system_prompt)
            if success:
                return success, response
        
        return False, "All LLM providers failed to respond"
    
    def _try_provider(self, provider: str, model: str, prompt: str, 
                     system_prompt: Optional[str] = None) -> Tuple[bool, str]:
        """
        Try to get a response from a specific provider.
        
        Args:
            provider: LLM provider
            model: Model to use
            prompt: The prompt to send
            system_prompt: Optional system prompt
            
        Returns:
            Tuple of (success, response)
        """
        try:
            # Construct the model name for litellm
            model_name = self._get_litellm_model_name(provider, model)
            
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Call the LLM
            response = completion(
                model=model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            return True, response_text
            
        except Exception as e:
            self.logger.error(f"Error calling {provider} LLM: {str(e)}")
            return False, str(e)
    
    def _get_litellm_model_name(self, provider: str, model: str) -> str:
        """
        Get the model name in litellm format.
        
        Args:
            provider: LLM provider
            model: Model name
            
        Returns:
            Model name in litellm format
        """
        if provider == "ollama":
            return f"ollama/{model}"
        elif provider == "claude":
            return f"anthropic/{model}"
        elif provider == "openai":
            return f"openai/{model}"
        else:
            return model
    
    def _get_fallback_model(self, provider: str) -> Optional[str]:
        """
        Get an appropriate model for a fallback provider.
        
        Args:
            provider: Fallback provider
            
        Returns:
            Model name or None if not available
        """
        if provider == "claude":
            return "claude-3-opus-20240229"
        elif provider == "openai":
            return "gpt-4-turbo"
        elif provider == "ollama":
            return "deepseek-r1"
        else:
            return None
    
    def is_available(self) -> bool:
        """
        Check if the LLM is available.
        
        Returns:
            True if the LLM is available, False otherwise
        """
        try:
            # Try a simple completion to check if the LLM is available
            success, _ = self.analyze("Hello, are you available?", "Respond with 'yes' if you can see this message.")
            return success
        except Exception as e:
            self.logger.error(f"LLM not available: {str(e)}")
            return False


# Singleton instance
llm_analyzer = LLMAnalyzer() 