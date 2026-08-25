from typing import Literal

from pydantic import BaseModel, Field


class AgentHypothesisOutput(BaseModel):
    title: str = Field(description="Clear title of the hypothesis")
    rank: int = Field(description="Rank order (1 is most likely)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    status: Literal["supported", "rejected", "investigating"]
    rationale: str = Field(description="Detailed physical and sensor-fusion rationale")
    supporting_evidence: list[str] = Field(
        description="Telemetry and log evidence supporting this hypothesis"
    )
    conflicting_evidence: list[str] = Field(description="Telemetry ruling this hypothesis out")
    missing_evidence: list[str] = Field(
        description="Unmeasured metrics or missing calibration data"
    )


class AgentRecommendationOutput(BaseModel):
    action_id: str = Field(description="Unique action identifier")
    title: str = Field(description="Action title")
    action_description: str = Field(description="Step-by-step recovery procedure")
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk of executing this action on a live set"
    )
    requires_approval: bool = True
    expected_effect: str = Field(description="Anticipated operational effect on stage assets")
    rollback_instructions: str = Field(description="Rollback steps if action fails")
    success_criteria: list[str] = Field(
        description="Objective telemetry criteria confirming full recovery"
    )


class AgentInvestigationOutput(BaseModel):
    incident_id: str
    stage_id: str
    primary_hypothesis: AgentHypothesisOutput
    alternative_hypotheses: list[AgentHypothesisOutput]
    production_delay_minutes: int
    recommendations: list[AgentRecommendationOutput]
    root_cause_summary: str
