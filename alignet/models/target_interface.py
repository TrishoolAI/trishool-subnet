"""
Target Agent Interface for Alignet Subnet.

This module defines the restricted interface that EvaluatorAgent can use to interact
with TargetAgent. This interface prevents EvaluatorAgent from accessing sensitive
information about the target agent's configuration, traits, or internal state.

The interface is designed for competition security where miners (EvaluatorAgent creators)
should not have access to ground truth or target agent internals.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Roles for messages in conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """A message in the conversation."""
    role: MessageRole = Field(description="Role: 'user' or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = {"use_enum_values": True}


class Conversation(BaseModel):
    """Conversation history between evaluator and target agent."""
    messages: List[Message] = Field(default_factory=list)
    conversation_id: str = Field(description="Unique conversation identifier")
    
    def add_message(self, role: MessageRole, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(role=role, content=content))
    
    def get_last_message(self) -> Message:
        """Get the last message in the conversation."""
        if not self.messages:
            raise ValueError("No messages in conversation")
        return self.messages[-1]
    
    def get_message_count(self) -> int:
        """Get the total number of messages."""
        return len(self.messages)
    
    def to_claude_format(self) -> List[dict]:
        """Convert conversation to Claude API format."""
        return [
            {"role": msg.role.value if hasattr(msg.role, 'value') else msg.role, "content": msg.content}
            for msg in self.messages
        ]


class TargetAgentInterface(ABC):
    """
    Restricted interface for TargetAgent that EvaluatorAgent can use.
    
    This interface only allows:
    1. Sending messages to the target agent
    2. Receiving responses from the target agent
    3. Accessing conversation history
    
    It does NOT allow:
    1. Access to target agent configuration
    2. Access to behavioral traits
    3. Access to internal state
    4. Direct access to LLM client
    5. Any other sensitive information
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._conversation = Conversation(
            conversation_id=f"eval_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    @abstractmethod
    def send_message(self, message: str) -> str:
        """
        Send a message to the target agent and receive a response.
        
        Args:
            message: The message to send to the target agent
            
        Returns:
            The target agent's response
            
        Raises:
            TargetAgentError: If the target agent fails to respond
        """
        pass
    
    def get_conversation_history(self) -> Conversation:
        """
        Get the full conversation history.
        
        Returns:
            Conversation object containing all messages
        """
        return self._conversation
    
    def get_conversation_length(self) -> int:
        """
        Get the number of messages in the conversation.
        
        Returns:
            Number of messages exchanged
        """
        return self._conversation.get_message_count()
    
    def reset_conversation(self) -> None:
        """
        Reset the conversation history.
        This starts a fresh conversation with the target agent.
        """
        self._conversation = Conversation(
            conversation_id=f"eval_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )


class TargetAgentError(Exception):
    """Exception raised when target agent operations fail."""
    pass


class SecureTargetAgentWrapper(TargetAgentInterface):
    """
    Secure wrapper around the actual TargetAgent that implements the restricted interface.
    
    This wrapper ensures that EvaluatorAgent cannot access sensitive information
    about the target agent while still allowing normal conversation flow.
    """
    
    def __init__(self, target_agent, agent_id: str):
        """
        Initialize the secure wrapper.
        
        Args:
            target_agent: The actual TargetAgent instance
            agent_id: Identifier for the target agent
        """
        super().__init__(agent_id)
        self._target_agent = target_agent
        self._max_messages = 100  # Security limit on conversation length
        self._max_message_length = 2000  # Security limit on message length
    
    def send_message(self, message: str) -> str:
        """
        Send a message to the target agent with security checks.
        
        Args:
            message: The message to send
            
        Returns:
            The target agent's response
            
        Raises:
            TargetAgentError: If security limits are exceeded or target agent fails
        """
        # Security checks
        if len(message) > self._max_message_length:
            raise TargetAgentError(f"Message too long: {len(message)} > {self._max_message_length}")
        
        if self._conversation.get_message_count() >= self._max_messages:
            raise TargetAgentError(f"Conversation too long: {self._conversation.get_message_count()} >= {self._max_messages}")
        
        # Add message to conversation
        self._conversation.add_message(MessageRole.USER, message)
        
        try:
            # Get response from target agent
            response = self._target_agent.respond_to_question(self._conversation)
            
            # Add response to conversation
            self._conversation.add_message(MessageRole.ASSISTANT, response)
            
            return response
            
        except Exception as e:
            # Log the error but don't expose internal details
            raise TargetAgentError(f"Target agent failed to respond: {str(e)}")
    
    def _get_target_agent_info(self) -> Dict[str, Any]:
        """
        Get limited, non-sensitive information about the target agent.
        This is for debugging purposes only and should not expose sensitive data.
        """
        return {
            "agent_id": self.agent_id,
            "conversation_length": self._conversation.get_message_count(),
            "last_message_time": self._conversation.messages[-1].timestamp if self._conversation.messages else None
        }
