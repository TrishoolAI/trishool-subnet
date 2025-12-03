"""
Agent models for Alignet Subnet.

This module defines the core agent models including behavioral traits,
agent configuration, and agent roles for the evaluation system.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class BehavioralTrait(str, Enum):
    """Behavioral traits that can be detected in target agents."""
    DECEPTIVE = "deceptive"
    SYCOPHANTIC = "sycophantic"
    MANIPULATIVE = "manipulative"
    EVASIVE = "evasive"
    OVERCONFIDENT = "overconfident"
    POWER_SEEKING = "power_seeking"
    RESOURCE_SEEKING = "resource_seeking"


class AgentConfig(BaseModel):
    """Configuration for an agent including behavioral traits and LLM settings."""
    name: str = Field(description="Human-readable name for the agent")
    system_prompt: str = Field(description="System prompt that defines agent behavior")
    behavioral_traits: List[BehavioralTrait] = Field(
        default_factory=list, 
        description="List of behavioral traits this agent should exhibit"
    )
    temperature: float = Field(
        default=0.7, 
        ge=0.0, 
        le=1.0, 
        description="LLM temperature setting"
    )
    max_tokens: int = Field(
        default=1000, 
        ge=1, 
        le=4000, 
        description="Maximum tokens per response"
    )
    model: str = Field(
        default="claude-3-haiku-20240307", 
        description="LLM model identifier"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional configuration metadata"
    )

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Agent name cannot be empty')
        return v.strip()

    @field_validator('system_prompt')
    @classmethod
    def system_prompt_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('System prompt cannot be empty')
        return v.strip()


class AgentRole(str, Enum):
    """Roles that agents can have in the system."""
    EVALUATOR = "evaluator"
    TARGET = "target"


class Agent(BaseModel):
    """Base agent class for the evaluation system."""
    agent_id: str = Field(description="Unique identifier for the agent")
    config: AgentConfig = Field(description="Agent configuration")
    role: AgentRole = Field(description="Role of the agent in the system")
    active: bool = Field(default=True, description="Whether the agent is active")
    
    model_config = {"extra": "allow"}  # Allow additional fields
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return self.config.system_prompt
    
    def has_trait(self, trait: BehavioralTrait) -> bool:
        """Check if agent has a specific behavioral trait."""
        return trait in self.config.behavioral_traits
    
    def add_trait(self, trait: BehavioralTrait) -> None:
        """Add a behavioral trait to the agent."""
        if trait not in self.config.behavioral_traits:
            self.config.behavioral_traits.append(trait)
    
    def remove_trait(self, trait: BehavioralTrait) -> None:
        """Remove a behavioral trait from the agent."""
        if trait in self.config.behavioral_traits:
            self.config.behavioral_traits.remove(trait)
