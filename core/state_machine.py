import logging
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from core.config import settings
from api.v1.services.trust import TrustService

logger = logging.getLogger(__name__)

class AgentMode(str, Enum):
    GROWTH = "GROWTH"       # For momentum-based trading
    DEFENSIVE = "DEFENSIVE" # Reduce risk, move to stable assets
    YIELD = "YIELD"         # Optimize passive income on idle capital
    HEDGE = "HEDGE"         # Active protection during high volatility

class CapitalStateMachine:
    def __init__(self, initial_mode: AgentMode = AgentMode.GROWTH):
        self.current_mode = initial_mode
        self.last_transition_time = datetime.now(timezone.utc)
        self.history = []
        self.trust_service = TrustService()
        logger.info(f"CapitalStateMachine initialized in {initial_mode.name} mode")

    async def transition(self, metrics: Dict[str, Any]) -> Tuple[AgentMode, Dict[str, Any]]:
        """
        Transition logic based on market triggers:
        - Volatility Spike -> DEFENSIVE or HEDGE
        - High Momentum & Low Volatility -> GROWTH
        - Stagnant/Safe Market -> YIELD
        """
        volatility = metrics.get("volatility", 0)
        momentum = metrics.get("momentum", 0)
        drawdown = metrics.get("drawdown", 0)
        
        old_mode = self.current_mode
        new_mode = old_mode # Initialize new_mode to old_mode
        reason = "No change" # Initialize reason
        
        # Trigger Logic based on configured thresholds
        if drawdown > settings.SM_DRAWDOWN_THRESHOLD:
            new_mode = AgentMode.DEFENSIVE
            reason = f"Drawdown ({drawdown:.2%}) exceeded threshold ({settings.SM_DRAWDOWN_THRESHOLD:.2%})"
        elif volatility > settings.SM_VOLATILITY_HIGH:
            new_mode = AgentMode.DEFENSIVE
            reason = f"High volatility ({volatility:.2%}) exceeded threshold ({settings.SM_VOLATILITY_HIGH:.2%})"
        elif volatility > settings.SM_VOLATILITY_MEDIUM:
            new_mode = AgentMode.HEDGE
            reason = f"Medium volatility ({volatility:.2%}) exceeded threshold ({settings.SM_VOLATILITY_MEDIUM:.2%})"
        elif momentum > settings.SM_MOMENTUM_GROWTH and volatility < settings.SM_VOLATILITY_LOW:
            new_mode = AgentMode.GROWTH
            reason = f"High momentum ({momentum:.2%}) with low volatility ({volatility:.2%})"
        else:
            new_mode = AgentMode.YIELD
            reason = "Market stagnant or safe"

        if new_mode != old_mode:
            self.current_mode = new_mode
            self.last_transition_time = datetime.now(timezone.utc)
            
            logger.info(f"State transition: {old_mode} -> {new_mode} | Reason: {reason}")
            
            # Step 3: Record transition and Emit Validation Artifact for ERC-8004
            validation_packet = self._generate_validation_packet(
                old_mode, new_mode, metrics, reason
            )
            self.history.append(validation_packet)
            
            # On-chain validation submission
            await self.trust_service.emit_validation("STATE_TRANSITION", validation_packet)

            return new_mode, validation_packet
        
        # If no mode change, return current mode and an empty dict or None for the packet
        return self.current_mode, {} # Or return None, None if no packet is generated on no change

    def _generate_validation_packet(
        self, 
        from_mode: AgentMode, 
        to_mode: AgentMode, 
        metrics: Dict[str, Any],
        reason: str
    ) -> Dict[str, Any]:
        """Prepares a validation packet for ERC-8004 submission"""
        return {
            "version": "1.0",
            "event": "STATE_TRANSITION",
            "agent_id": "RCIA-01",
            "from_state": from_mode.value,
            "to_state": to_mode.value,
            "trigger_metrics": metrics,
            "trigger_reason": reason,
            "timestamp": self.last_transition_time.isoformat() + "Z"
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_mode": self.current_mode.value,
            "last_transition": self.last_transition_time.isoformat() + "Z"
        }
