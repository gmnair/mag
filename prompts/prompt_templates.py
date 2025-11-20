"""Prompt template system using Template Method design pattern."""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from string import Template
import yaml
import os

logger = logging.getLogger(__name__)


class PromptTemplate(ABC):
    """Abstract base class for prompt templates."""
    
    def __init__(self, template_string: str, variables: Optional[Dict[str, Any]] = None):
        self.template_string = template_string
        self.variables = variables or {}
        self.template = Template(template_string)
    
    def render(self, **kwargs) -> str:
        """Render template with provided variables."""
        # Merge instance variables with provided kwargs
        all_vars = {**self.variables, **kwargs}
        
        # Safe substitute - handles missing variables gracefully
        try:
            return self.template.safe_substitute(**all_vars)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return self.template_string
    
    @abstractmethod
    def get_system_message(self) -> Optional[str]:
        """Get system message for this prompt template."""
        pass
    
    def format_variables(self, **kwargs) -> Dict[str, Any]:
        """Format variables for template substitution."""
        return kwargs


class DeepAgentPerceptionTemplate(PromptTemplate):
    """Template for Deep Agent perception phase."""
    
    def __init__(self):
        super().__init__(
            template_string="""You are an intelligent agent analyzing a situation. Based on the following context and goals, provide your perception:

Context:
${context}

Goals:
${goals}

Available Tools: ${tool_count}
Available Agents: ${agent_count}

Provide your perception in JSON format with:
- understanding: Your understanding of the current situation
- relevant_context: Key information from context
- priority: Priority level (high/medium/low)
- next_steps: Suggested next steps"""
        )
    
    def get_system_message(self) -> Optional[str]:
        return "You are an intelligent agent capable of analyzing complex situations and providing insightful perceptions."
    
    def format_variables(
        self,
        context: str,
        goals: list,
        tool_count: int,
        agent_count: int
    ) -> Dict[str, Any]:
        """Format variables for perception template."""
        goals_str = "\n".join(goals) if isinstance(goals, list) else str(goals)
        return {
            "context": context,
            "goals": goals_str,
            "tool_count": tool_count,
            "agent_count": agent_count
        }


class DeepAgentPlanningTemplate(PromptTemplate):
    """Template for Deep Agent planning phase."""
    
    def __init__(self):
        super().__init__(
            template_string="""Based on your perception and goals, create an execution plan.

Perception:
${perception}

Goals:
${goals}

Available Tools:
${tools}

Available Agents:
${agents}

Create a step-by-step execution plan. Each step should have:
- step_number: Sequential number
- action: What to do
- tool_or_agent: Which tool/agent to use
- description: Why this step
- expected_outcome: What to expect

Return as JSON array of steps."""
        )
    
    def get_system_message(self) -> Optional[str]:
        return "You are a strategic planning agent that creates detailed, actionable execution plans."
    
    def format_variables(
        self,
        perception: str,
        goals: list,
        tools: list,
        agents: list
    ) -> Dict[str, Any]:
        """Format variables for planning template."""
        goals_str = "\n".join(f"- {goal}" for goal in goals) if isinstance(goals, list) else str(goals)
        tools_str = "\n".join(
            f"- {tool.get('name', 'Unknown')}: {tool.get('description', '')}"
            for tool in tools[:5]
        ) if isinstance(tools, list) else str(tools)
        agents_str = "\n".join(
            f"- {agent.get('id', 'Unknown')}: {agent.get('capabilities', '')}"
            for agent in agents[:5]
        ) if isinstance(agents, list) else str(agents)
        
        return {
            "perception": perception,
            "goals": goals_str,
            "tools": tools_str,
            "agents": agents_str
        }


class DeepAgentLearningTemplate(PromptTemplate):
    """Template for Deep Agent learning phase."""
    
    def __init__(self):
        super().__init__(
            template_string="""Analyze the execution results and provide learning insights.

Plan:
${plan}

Execution Results:
${execution_results}

Provide learning insights:
- outcome: Overall outcome (success/partial/failure)
- lessons: Key lessons learned
- context_updates: What should be updated in context for future reference
- improvements: Suggestions for improvement

Return as JSON."""
        )
    
    def get_system_message(self) -> Optional[str]:
        return "You are a learning agent that analyzes outcomes and extracts valuable insights for continuous improvement."
    
    def format_variables(
        self,
        plan: list,
        execution_results: list
    ) -> Dict[str, Any]:
        """Format variables for learning template."""
        plan_str = "\n".join(
            f"Step {step.get('step_number', '?')}: {step.get('action', 'Unknown')}"
            for step in plan
        ) if isinstance(plan, list) else str(plan)
        
        results_str = "\n".join(
            f"- {result.get('status', 'Unknown')}: {result.get('message', '')}"
            for result in execution_results
        ) if isinstance(execution_results, list) else str(execution_results)
        
        return {
            "plan": plan_str,
            "execution_results": results_str
        }


class SCAPAnalysisTemplate(PromptTemplate):
    """Template for SCAP agent transaction analysis."""
    
    def __init__(self):
        super().__init__(
            template_string="""Analyze the following flagged transactions for case ${case_id} and provide a comprehensive summary.

Flagged Transactions:
${flagged_transactions}

Please provide:
1. Overall risk assessment
2. Key patterns or concerns
3. Recommended actions
4. Summary of flagged transactions by country/jurisdiction"""
        )
    
    def get_system_message(self) -> Optional[str]:
        return "You are a financial compliance analyst specializing in transaction risk assessment and sensitive country analysis."
    
    def format_variables(
        self,
        case_id: str,
        flagged_transactions: str
    ) -> Dict[str, Any]:
        """Format variables for SCAP analysis template."""
        return {
            "case_id": case_id,
            "flagged_transactions": flagged_transactions
        }


class PromptTemplateManager:
    """Manager for prompt templates with loading from YAML configuration."""
    
    def __init__(self, config_file: str = None):
        self.templates: Dict[str, PromptTemplate] = {}
        from config import Config
        self.config_file = config_file or Config.PROMPTS_CONFIG_FILE
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from YAML configuration or use defaults."""
        # Register default templates
        self.templates = {
            "deep_agent_perception": DeepAgentPerceptionTemplate(),
            "deep_agent_planning": DeepAgentPlanningTemplate(),
            "deep_agent_learning": DeepAgentLearningTemplate(),
            "scap_analysis": SCAPAnalysisTemplate()
        }
        
        # Try to load from YAML file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    if config:
                        self._load_from_config(config)
            except Exception as e:
                logger.warning(f"Could not load prompts from {self.config_file}: {str(e)}")
    
    def _load_from_config(self, config: Dict[str, Any]):
        """Load templates from YAML configuration."""
        for template_name, template_config in config.get("templates", {}).items():
            if template_config.get("enabled", True):
                template_string = template_config.get("template", "")
                system_message = template_config.get("system_message", "")
                
                # Create custom template class dynamically
                class CustomTemplate(PromptTemplate):
                    def __init__(self, template_str, sys_msg):
                        super().__init__(template_str)
                        self._system_message = sys_msg
                    
                    def get_system_message(self):
                        return self._system_message
                
                self.templates[template_name] = CustomTemplate(template_string, system_message)
                logger.info(f"Loaded custom template: {template_name}")
    
    def get_template(self, template_name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self.templates.get(template_name)
    
    def render_template(self, template_name: str, **kwargs) -> str:
        """Render a template by name with provided variables."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        formatted_vars = template.format_variables(**kwargs)
        return template.render(**formatted_vars)
    
    def get_system_message(self, template_name: str) -> Optional[str]:
        """Get system message for a template."""
        template = self.get_template(template_name)
        return template.get_system_message() if template else None


# Global template manager instance
_template_manager: Optional[PromptTemplateManager] = None


def get_template_manager() -> PromptTemplateManager:
    """Get global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = PromptTemplateManager()
    return _template_manager

