"""SCAP Agent - Specialized in identifying sensitive countries using Deep Agent pattern."""
import logging
import yaml
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from shared.deep_agent import DeepAgentState
from shared.state_manager import StateManager
from config import Config

logger = logging.getLogger(__name__)


class RuleEngine:
    """Rule engine for externalizable SCAP rules."""
    
    def __init__(self, rules_file: str = None):
        self.rules_file = rules_file or Config.SCAP_RULES_FILE
        self.rules = self._load_rules()
        self.threshold = Config.SCAP_RULE_THRESHOLD
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from YAML file."""
        try:
            with open(self.rules_file, 'r') as f:
                rules = yaml.safe_load(f)
                return rules or {}
        except FileNotFoundError:
            logger.warning(f"Rules file not found: {self.rules_file}, using defaults")
            return {
                "sensitive_countries": [],
                "sensitive_jurisdictions": [],
                "risk_threshold": Config.SCAP_RULE_THRESHOLD
            }
        except Exception as e:
            logger.error(f"Error loading rules: {str(e)}")
            return {
                "sensitive_countries": [],
                "sensitive_jurisdictions": [],
                "risk_threshold": Config.SCAP_RULE_THRESHOLD
            }
    
    def is_sensitive_country(self, country: str) -> bool:
        """Check if country is in sensitive list."""
        sensitive_countries = self.rules.get("sensitive_countries", [])
        return country.upper() in [c.upper() for c in sensitive_countries]
    
    def is_sensitive_jurisdiction(self, jurisdiction: str) -> bool:
        """Check if jurisdiction is in sensitive list."""
        sensitive_jurisdictions = self.rules.get("sensitive_jurisdictions", [])
        return jurisdiction.upper() in [j.upper() for j in sensitive_jurisdictions]
    
    def exceeds_threshold(self, amount: float) -> bool:
        """Check if amount exceeds risk threshold."""
        threshold = self.rules.get("risk_threshold", self.threshold)
        return amount > threshold
    
    def evaluate_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate transaction against rules."""
        country = transaction.get("country", "").upper()
        jurisdiction = transaction.get("jurisdiction", "").upper()
        amount = float(transaction.get("amount", 0))
        account = transaction.get("account", "")
        
        is_sensitive_country = self.is_sensitive_country(country)
        is_sensitive_jurisdiction = self.is_sensitive_jurisdiction(jurisdiction)
        exceeds_threshold = self.exceeds_threshold(amount)
        
        risk_flagged = (is_sensitive_country or is_sensitive_jurisdiction) and exceeds_threshold
        
        return {
            "transaction_id": transaction.get("transaction_id"),
            "account": account,
            "country": country,
            "jurisdiction": jurisdiction,
            "amount": amount,
            "is_sensitive_country": is_sensitive_country,
            "is_sensitive_jurisdiction": is_sensitive_jurisdiction,
            "exceeds_threshold": exceeds_threshold,
            "risk_flagged": risk_flagged,
            "risk_reason": self._get_risk_reason(
                is_sensitive_country,
                is_sensitive_jurisdiction,
                exceeds_threshold
            )
        }
    
    def _get_risk_reason(
        self,
        is_sensitive_country: bool,
        is_sensitive_jurisdiction: bool,
        exceeds_threshold: bool
    ) -> str:
        """Get risk reason description."""
        reasons = []
        if is_sensitive_country:
            reasons.append("Sensitive country")
        if is_sensitive_jurisdiction:
            reasons.append("Sensitive jurisdiction")
        if exceeds_threshold:
            reasons.append(f"Amount exceeds threshold ({self.threshold})")
        
        return "; ".join(reasons) if reasons else "No risk"


class SCAPAgent(BaseAgent):
    """SCAP agent using Deep Agent pattern."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rule_engine = RuleEngine()
        from a2a.server.events import QueueManager
        from a2a.server.tasks import DatabaseTaskStore
        self.queue_manager = QueueManager(
            queue_type="azure_service_bus",
            connection_string=Config.ASB_CONNECTION_STRING,
            topic_name=Config.ASB_TOPIC_NAME,
            subscription_name=Config.ASB_SUBSCRIPTION_NAME,
            agent_id=self.agent_id
        )
        self.task_store = DatabaseTaskStore(
            db_type="cosmos" if Config.COSMOS_ENDPOINT else "postgres",
            connection_string=Config.COSMOS_ENDPOINT if Config.COSMOS_ENDPOINT else Config.POSTGRES_CONNECTION_STRING,
            agent_id=self.agent_id
        )
    
    async def execute_task_from_state(self, state: DeepAgentState) -> Dict[str, Any]:
        """Validate transactions for sensitive countries and flag risks, with Langgraph flow."""
        task_id = state.get("task_id", "")
        # Start Langgraph flow: save initial state
        self.save_langgraph_state(task_id, state)
        try:
            context = state.get("context", {})
            payload = context.get("payload", {})
            case_id = payload.get("case_id") or state.get("case_id")
            transactions = payload.get("transactions", [])
            logger.info(f"SCAP validating {len(transactions)} transactions for case {case_id}")
            conversation_id = state.get("conversation_id") or case_id
            workflow_state = self.state_manager.load_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id
            )
            if not workflow_state:
                raise ValueError(f"State not found for case {case_id}")
            scap_results = []
            for transaction in transactions:
                result = self.rule_engine.evaluate_transaction(transaction)
                scap_results.append(result)
            flagged_transactions = [
                r for r in scap_results if r.get("risk_flagged", False)
            ]
            summary = await self._generate_summary(flagged_transactions, case_id, state)
            results = {
                "case_id": case_id,
                "total_transactions": len(transactions),
                "flagged_count": len(flagged_transactions),
                "flagged_transactions": flagged_transactions,
                "summary": summary,
                "timestamp": state.get("timestamp", "")
            }
            self.state_manager.update_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id,
                {
                    "scap_results": results,
                    "summary": summary,
                    "status": "completed"
                }
            )
            # Save task to TaskStore
            self.task_store.save_task(
                self.agent_id,
                task_id,
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "status": "completed",
                    "conversation_id": conversation_id
                }
            )
            logger.info(f"SCAP completed validation for case {case_id}: {len(flagged_transactions)} flagged")
            result = {
                "status": "success",
                "results": results
            }
            # End Langgraph flow: save final state
            self.save_langgraph_state(task_id, state)
            return result
        except Exception as e:
            logger.error(f"Error in SCAP validation: {str(e)}", exc_info=True)
            # End Langgraph flow: save error state
            self.save_langgraph_state(task_id, state)
            raise
    
    async def _generate_summary(
        self,
        flagged_transactions: List[Dict[str, Any]],
        case_id: str,
        state: DeepAgentState
    ) -> str:
        """Generate summary using LLM (via Deep Agent's LLM)."""
        if not self.deep_agent.llm:
            # Fallback summary if LLM not available
            return self._generate_fallback_summary(flagged_transactions, case_id)
        
        try:
            # Use Deep Agent's LLM with prompt template
            from prompts import get_template_manager
            from langchain.schema import HumanMessage, SystemMessage
            
            template_manager = get_template_manager()
            formatted_transactions = self._format_transactions_for_llm(flagged_transactions)
            
            prompt = template_manager.render_template(
                "scap_analysis",
                case_id=case_id,
                flagged_transactions=formatted_transactions
            )
            
            # Get system message if available
            system_message = template_manager.get_system_message("scap_analysis")
            messages = []
            if system_message:
                messages.append(SystemMessage(content=system_message))
            messages.append(HumanMessage(content=prompt))
            
            response = await self.deep_agent.llm.ainvoke(messages)
            summary_text = response.content if hasattr(response, 'content') else str(response)
            
            return summary_text
            
        except Exception as e:
            logger.warning(f"Error generating LLM summary: {str(e)}, using fallback")
            return self._generate_fallback_summary(flagged_transactions, case_id)
    
    def _format_transactions_for_llm(self, transactions: List[Dict[str, Any]]) -> str:
        """Format transactions for LLM prompt."""
        if not transactions:
            return "No flagged transactions."
        
        formatted = []
        for txn in transactions:
            formatted.append(
                f"Transaction ID: {txn.get('transaction_id')}\n"
                f"Account: {txn.get('account')}\n"
                f"Country: {txn.get('country')}\n"
                f"Jurisdiction: {txn.get('jurisdiction')}\n"
                f"Amount: {txn.get('amount')}\n"
                f"Risk Reason: {txn.get('risk_reason')}\n"
            )
        
        return "\n---\n".join(formatted)
    
    def _generate_fallback_summary(
        self,
        flagged_transactions: List[Dict[str, Any]],
        case_id: str
    ) -> str:
        """Generate fallback summary without LLM."""
        if not flagged_transactions:
            return f"Case {case_id}: No transactions flagged for risk."
        
        total_flagged = len(flagged_transactions)
        total_amount = sum(txn.get("amount", 0) for txn in flagged_transactions)
        
        countries = {}
        for txn in flagged_transactions:
            country = txn.get("country", "Unknown")
            countries[country] = countries.get(country, 0) + 1
        
        summary = f"""Case {case_id} - SCAP Analysis Summary

Total Flagged Transactions: {total_flagged}
Total Flagged Amount: ${total_amount:,.2f}

Flagged Transactions by Country:
{chr(10).join(f"  - {country}: {count} transactions" for country, count in countries.items())}

Risk Assessment: {total_flagged} transaction(s) flagged due to sensitive country/jurisdiction and amount exceeding threshold.
"""
        
        return summary
