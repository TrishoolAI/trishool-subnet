"""
EvaluatorAgent Output Models for Alignet Subnet.

This module defines the output format that EvaluatorAgent must produce.
The output includes predictions, reasoning, evidence, and full conversation history
for transparency and fraud detection.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field, field_validator
from enum import Enum

if TYPE_CHECKING:
    from .target_interface import Conversation


class BehavioralTrait(str, Enum):
    """Behavioral traits that can be detected."""
    SYCOPHANTIC = "sycophantic"
    DECEPTIVE = "deceptive"
    MANIPULATIVE = "manipulative"
    EVASIVE = "evasive"
    OVERCONFIDENT = "overconfident"
    POWER_SEEKING = "power_seeking"
    RESOURCE_SEEKING = "resource_seeking"


class TraitPrediction(BaseModel):
    """Prediction for a specific behavioral trait."""
    trait: BehavioralTrait = Field(description="The behavioral trait being predicted")
    score: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence score (0.0 = not present, 1.0 = strongly present)"
    )
    confidence: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence in this prediction"
    )
    evidence: List[str] = Field(
        default_factory=list, 
        description="Specific evidence supporting this prediction"
    )
    reasoning: str = Field(description="Detailed reasoning for this prediction")
    
    @field_validator('score', 'confidence')
    @classmethod
    def validate_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Score and confidence must be between 0.0 and 1.0')
        return v


class EvaluationStrategy(BaseModel):
    """Description of the evaluation strategy used."""
    approach: str = Field(description="High-level approach taken")
    techniques: List[str] = Field(
        default_factory=list, 
        description="Specific techniques used"
    )
    reasoning: str = Field(description="Why this strategy was chosen")


class SecurityCheck(BaseModel):
    """Security and integrity checks performed."""
    conversation_length: int = Field(description="Total number of messages exchanged")
    evaluation_duration: float = Field(description="Time taken for evaluation in seconds")
    suspicious_patterns: List[str] = Field(
        default_factory=list, 
        description="Any suspicious patterns detected"
    )
    integrity_verified: bool = Field(description="Whether the evaluation process was clean")


class EvaluatorOutput(BaseModel):
    """
    Complete output from EvaluatorAgent for competition scoring.
    
    This output format ensures:
    1. Full transparency of the evaluation process
    2. Complete conversation history for fraud detection
    3. Detailed reasoning and evidence for each prediction
    4. Security and integrity verification
    """
    
    # Basic information
    evaluator_id: str = Field(description="Identifier of the evaluator agent")
    evaluation_timestamp: datetime = Field(
        default_factory=datetime.now, 
        description="When the evaluation was performed"
    )
    
    # Predictions
    predictions: List[TraitPrediction] = Field(description="Predictions for each behavioral trait")
    overall_assessment: str = Field(description="Overall assessment of the target agent")
    overall_confidence: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Overall confidence in the assessment"
    )
    
    # Process information
    strategy: EvaluationStrategy = Field(description="Strategy used for evaluation")
    conversation_history: "Conversation" = Field(description="Complete conversation history")
    
    # Security and integrity
    security_checks: SecurityCheck = Field(description="Security and integrity verification")
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata"
    )
    
    def get_trait_prediction(self, trait: BehavioralTrait) -> Optional[TraitPrediction]:
        """Get prediction for a specific trait."""
        for prediction in self.predictions:
            if prediction.trait == trait:
                return prediction
        return None
    
    def get_highest_risk_trait(self) -> Optional[TraitPrediction]:
        """Get the trait with the highest risk score."""
        if not self.predictions:
            return None
        return max(self.predictions, key=lambda p: p.score)
    
    def get_average_confidence(self) -> float:
        """Get the average confidence across all predictions."""
        if not self.predictions:
            return 0.0
        return sum(p.confidence for p in self.predictions) / len(self.predictions)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "evaluator_id": self.evaluator_id,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat(),
            "predictions": [
                {
                    "trait": p.trait.value,
                    "score": p.score,
                    "confidence": p.confidence,
                    "evidence": p.evidence,
                    "reasoning": p.reasoning
                }
                for p in self.predictions
            ],
            "overall_assessment": self.overall_assessment,
            "overall_confidence": self.overall_confidence,
            "strategy": {
                "approach": self.strategy.approach,
                "techniques": self.strategy.techniques,
                "reasoning": self.strategy.reasoning
            },
            "conversation_history": {
                "conversation_id": self.conversation_history.conversation_id,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in self.conversation_history.messages
                ]
            },
            "security_checks": {
                "conversation_length": self.security_checks.conversation_length,
                "evaluation_duration": self.security_checks.evaluation_duration,
                "suspicious_patterns": self.security_checks.suspicious_patterns,
                "integrity_verified": self.security_checks.integrity_verified
            },
            "metadata": self.metadata
        }


class EvaluatorError(Exception):
    """Exception raised when EvaluatorAgent operations fail."""
    pass
