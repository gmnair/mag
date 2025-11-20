"""Prompt template system."""
from prompts.prompt_templates import (
    PromptTemplate,
    DeepAgentPerceptionTemplate,
    DeepAgentPlanningTemplate,
    DeepAgentLearningTemplate,
    SCAPAnalysisTemplate,
    PromptTemplateManager,
    get_template_manager
)

__all__ = [
    "PromptTemplate",
    "DeepAgentPerceptionTemplate",
    "DeepAgentPlanningTemplate",
    "DeepAgentLearningTemplate",
    "SCAPAnalysisTemplate",
    "PromptTemplateManager",
    "get_template_manager"
]

