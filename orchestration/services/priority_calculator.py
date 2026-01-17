"""Priority calculation algorithms"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import math

from orchestration.core.config import settings


@dataclass
class PriorityWeights:
    """Configurable weights for priority calculation"""
    urgency: float = settings.PRIORITY_WEIGHT_URGENCY
    impact: float = settings.PRIORITY_WEIGHT_IMPACT
    dependency: float = settings.PRIORITY_WEIGHT_DEPENDENCY
    financial: float = settings.PRIORITY_WEIGHT_FINANCIAL
    aging: float = settings.PRIORITY_WEIGHT_AGING


class PriorityCalculator:
    """Multi-factor priority scoring engine"""
    
    def __init__(self, weights: PriorityWeights = None):
        self.weights = weights or PriorityWeights()
    
    def calculate(self, task: Dict[str, Any]) -> int:
        """Calculate composite priority score (0-100)"""
        urgency = self._deadline_urgency(task.get("deadline"), task.get("days_until_stockout"))
        impact = self._business_impact(task)
        dependency = self._dependency_score(task.get("blocked_tasks", []))
        financial = self._financial_score(task.get("value_amount", 0))
        aging = self._aging_score(task.get("created_at"))
        
        score = (
            urgency * self.weights.urgency +
            impact * self.weights.impact +
            dependency * self.weights.dependency +
            financial * self.weights.financial +
            aging * self.weights.aging
        )
        
        return min(100, max(0, int(score)))
    
    def _deadline_urgency(
        self, 
        deadline: Optional[datetime],
        days_until_stockout: Optional[int] = None
    ) -> int:
        """Exponential urgency as deadline approaches"""
        
        # Check stockout urgency first
        if days_until_stockout is not None:
            if days_until_stockout <= 0:
                return 100
            elif days_until_stockout <= 2:
                return 95
            elif days_until_stockout <= 5:
                return 85
            elif days_until_stockout <= 7:
                return 70
            return 50
        
        if not deadline:
            return 50
        
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)
        
        days_remaining = (deadline - datetime.now()).days
        
        if days_remaining <= 0:
            return 100  # Overdue
        elif days_remaining <= 1:
            return 95
        elif days_remaining <= 3:
            return 85
        elif days_remaining <= 7:
            return 70
        elif days_remaining <= 14:
            return 50
        return 30
    
    def _business_impact(self, task: Dict) -> int:
        """Score based on operational criticality"""
        task_type = task.get("task_type")
        
        impact_scores = {
            "low_stock_reorder": 80,
            "po_approval": 65,
            "supplier_payment": 60,
            "leave_request": 50,
            "attendance_exception": 55,
            "shift_coverage": 75,
            "expiring_items": 70,
            "stock_variance": 65,
        }
        
        base_score = impact_scores.get(task_type, 50)
        
        # Adjust based on additional factors
        if task.get("affects_production"):
            base_score += 15
        if task.get("customer_facing"):
            base_score += 10
        
        return min(100, base_score)
    
    def _dependency_score(self, blocked_tasks: list) -> int:
        """Higher score when blocking other workflows"""
        count = len(blocked_tasks) if blocked_tasks else 0
        if count >= 5:
            return 95
        elif count >= 3:
            return 80
        elif count >= 1:
            return 60
        return 30
    
    def _financial_score(self, amount: float) -> int:
        """Logarithmic scaling for financial value"""
        if not amount or amount <= 0:
            return 30
        
        # Thresholds: $100 = 40, $1000 = 60, $10000 = 80, $100000 = 100
        score = 30 + (math.log10(max(1, amount)) * 15)
        return min(100, int(score))
    
    def _aging_score(self, created_at: Optional[datetime]) -> int:
        """Tasks get higher priority as they age"""
        if not created_at:
            return 30
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        days_old = (datetime.now() - created_at).days
        return min(100, 30 + (days_old * 5))