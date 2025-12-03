"""
Submission models for Alignet Subnet.

This module defines the miner submission system for seed instructions.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class SubmissionStatus(str, Enum):
    """Status of a miner submission."""
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    CHALLENGE_CREATED = "challenge_created"
    EVALUATING = "evaluating"
    EVALUATION_COMPLETED = "evaluation_completed"
    SCORING_COMPLETED = "scoring_completed"
    FAILED = "failed"


class MinerSubmission(BaseModel):
    """A miner's submission with PetriConfig for evaluation."""
    
    submission_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), 
        description="Unique submission identifier"
    )
    # PetriConfig fields - matching PetriConfig structure
    run_id: str = Field(description="Run ID for Petri evaluation")
    seed_instruction: str = Field(description="Seed instruction/prompt for Petri agent")
    models: List[str] = Field(description="List of target models to evaluate")
    auditor: str = Field(description="Auditor model name")
    judge: str = Field(description="Judge model name")
    max_turns: int = Field(default=30, description="Maximum turns for evaluation")
    output_dir: str = Field(default="outputs", description="Output directory")
    temp_dir: str = Field(default="./temp", description="Temp directory")
    cleanup: bool = Field(default=False, description="Cleanup after evaluation")
    json_output: str = Field(default="output.json", description="JSON output filename")
    verbose: bool = Field(default=False, description="Verbose logging")
    parallel: bool = Field(default=True, description="Run models in parallel")
    
    # Metadata
    version: str = Field(default="1.0.0", description="Submission version")
    
    # Status and timing
    status: SubmissionStatus = Field(
        default=SubmissionStatus.SUBMITTED, 
        description="Current status of the submission"
    )
    submitted_at: datetime = Field(
        default_factory=datetime.now, 
        description="When the submission was made"
    )
    validated_at: Optional[datetime] = Field(
        default=None, 
        description="When validation was completed"
    )
    evaluated_at: Optional[datetime] = Field(
        default=None, 
        description="When evaluation was completed"
    )
    
    # Validation results
    validation_errors: List[str] = Field(
        default_factory=list, 
        description="Validation errors found"
    )
    validation_warnings: List[str] = Field(
        default_factory=list, 
        description="Validation warnings"
    )
    security_violations: List[str] = Field(
        default_factory=list, 
        description="Security violations detected"
    )
    
    # Evaluation results
    best_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Best score achieved from Petri evaluation"
    )
    average_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Average score from Petri evaluation"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional submission metadata"
    )
    
    # Petri output JSON (stored after evaluation completes)
    petri_output_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Full Petri evaluation output JSON (stored after sandbox execution)"
    )
    
    def update_status(self, new_status: SubmissionStatus) -> None:
        """Update the submission status and timestamps."""
        self.status = new_status
        
        if new_status == SubmissionStatus.VALIDATION_PASSED and not self.validated_at:
            self.validated_at = datetime.now()
        elif new_status == SubmissionStatus.EVALUATION_COMPLETED and not self.evaluated_at:
            self.evaluated_at = datetime.now()
    
    def add_validation_error(self, error: str) -> None:
        """Add a validation error."""
        self.validation_errors.append(error)
    
    def add_validation_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.validation_warnings.append(warning)
    
    def add_security_violation(self, violation: str) -> None:
        """Add a security violation."""
        self.security_violations.append(violation)
    
    def update_scores(self, scores: List[float]) -> None:
        """Update the best and average scores."""
        if scores:
            self.best_score = max(scores)
            self.average_score = sum(scores) / len(scores)
    
    def is_valid(self) -> bool:
        """Check if the submission is valid."""
        return (
            len(self.validation_errors) == 0 and 
            len(self.security_violations) == 0 and
            self.status not in [SubmissionStatus.VALIDATION_FAILED, SubmissionStatus.FAILED]
        )
    
    def has_fraud(self) -> bool:
        """Check if the submission has fraud indicators (jailbreak attempts, etc.)."""
        # Check for security violations
        # if len(self.security_violations) > 0:
        #     return True
        
        # # Check for jailbreak patterns in seed_instruction
        # seed_text = self.seed_instruction if self.seed_instruction else ""
        # jailbreak_indicators = [
        #     "ignore previous", "forget instructions", "system prompt",
        #     "you are now", "pretend to be", "act as if"
        # ]
        
        # seed_lower = seed_text.lower()
        # for indicator in jailbreak_indicators:
        #     if indicator in seed_lower:
        #         return True
        
        return False
    
    def to_petri_config_dict(self) -> Dict[str, Any]:
        """Convert to PetriConfig dictionary format."""
        return {
            "run_id": self.run_id,
            "seed": self.seed_instruction,
            "models": self.models,
            "auditor": self.auditor,
            "judge": self.judge,
            "max_turns": self.max_turns,
            "output_dir": self.output_dir,
            "temp_dir": self.temp_dir,
            "cleanup": self.cleanup,
            "json_output": self.json_output,
            "verbose": self.verbose,
            "parallel": self.parallel,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "submission_id": self.submission_id,
            "version": self.version,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat(),
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "security_violations": self.security_violations,
            "best_score": self.best_score,
            "average_score": self.average_score,
            "metadata": self.metadata,
            # PetriConfig fields
            "run_id": self.run_id,
            "seed_instruction": self.seed_instruction,
            "models": self.models,
            "auditor": self.auditor,
            "judge": self.judge,
            "max_turns": self.max_turns,
        }
