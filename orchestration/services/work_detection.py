"""Work detection service - queries pending work per role"""
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, union_all, literal, func

from orchestration.services.priority_calculator import PriorityCalculator


class WorkDetectionService:
    """Detects and prioritizes pending work per role"""
    
    def __init__(self, db: AsyncSession, priority_calc: PriorityCalculator):
        self.db = db
        self.calculator = priority_calc
    
    async def get_prioritized_work(
        self, 
        user_id: int, 
        role: str
    ) -> List[Dict[str, Any]]:
        """Query all pending work for a role, calculate live priorities"""
        
        # Route to role-specific detector
        role_detectors = {
            "purchase_manager": self._get_purchase_manager_work,
            "hr_manager": self._get_hr_manager_work,
            "inventory_manager": self._get_inventory_manager_work,
            "store_manager": self._get_store_manager_work,
            "supervisor": self._get_supervisor_work,
        }
        
        detector = role_detectors.get(role, self._get_default_work)
        tasks = await detector(user_id)
        
        # Calculate priorities and sort
        for task in tasks:
            task["calculated_priority"] = self.calculator.calculate(task)
            task["priority_level"] = self._get_priority_level(task["calculated_priority"])
        
        return sorted(tasks, key=lambda x: x["calculated_priority"], reverse=True)
    
    async def _get_purchase_manager_work(self, user_id: int) -> List[Dict]:
        """Get pending work for purchase manager"""
        tasks = []
        
        # Low stock alerts
        # In real implementation, query from your actual models
        # This is a placeholder structure
        low_stock_items = await self._query_low_stock_items()
        for item in low_stock_items:
            tasks.append({
                "task_type": "low_stock_reorder",
                "reference_id": item["id"],
                "reference_table": "items",
                "title": f"Reorder: {item['name']}",
                "description": f"Current: {item['current_stock']} {item['unit']}",
                "days_until_stockout": item.get("days_until_stockout", 30),
                "value_amount": item.get("estimated_order_value", 0),
                "created_at": item.get("alert_created_at", datetime.utcnow())
            })
        
        # Pending PO approvals
        pending_pos = await self._query_pending_po_approvals()
        for po in pending_pos:
            tasks.append({
                "task_type": "po_approval",
                "reference_id": po["id"],
                "reference_table": "purchase_orders",
                "title": f"Approve PO #{po['po_number']}",
                "description": f"Supplier: {po['supplier_name']}",
                "days_pending": po.get("days_pending", 0),
                "value_amount": po.get("total_amount", 0),
                "created_at": po.get("created_at", datetime.utcnow())
            })
        
        # Supplier payment dues
        payment_dues = await self._query_payment_dues()
        for payment in payment_dues:
            tasks.append({
                "task_type": "supplier_payment",
                "reference_id": payment["id"],
                "reference_table": "po_payments",
                "title": f"Payment due: {payment['supplier_name']}",
                "description": f"Amount: ${payment['amount']}",
                "deadline": payment.get("due_date"),
                "value_amount": payment.get("amount", 0),
                "created_at": payment.get("created_at", datetime.utcnow())
            })
        
        return tasks
    
    async def _get_hr_manager_work(self, user_id: int) -> List[Dict]:
        """Get pending work for HR manager"""
        tasks = []
        
        # Leave requests
        # Attendance exceptions
        # Salary processing
        # Shift coverage gaps
        
        # Placeholder - implement with actual queries
        return tasks
    
    async def _get_inventory_manager_work(self, user_id: int) -> List[Dict]:
        """Get pending work for inventory manager"""
        tasks = []
        
        # Stock counts due
        # Transfer requests
        # Expiring items
        # Variance investigations
        
        return tasks
    
    async def _get_store_manager_work(self, user_id: int) -> List[Dict]:
        """Get pending work for store manager - sees everything"""
        tasks = []
        
        # Aggregate from all departments
        tasks.extend(await self._get_purchase_manager_work(user_id))
        tasks.extend(await self._get_hr_manager_work(user_id))
        tasks.extend(await self._get_inventory_manager_work(user_id))
        
        return tasks
    
    async def _get_supervisor_work(self, user_id: int) -> List[Dict]:
        """Get pending work for supervisor"""
        # Limited subset of manager work
        return []
    
    async def _get_default_work(self, user_id: int) -> List[Dict]:
        """Default work detection for unknown roles"""
        return []
    
    # Placeholder query methods - implement with your actual models
    async def _query_low_stock_items(self) -> List[Dict]:
        """Query items below reorder level"""
        # Implement with actual SQLAlchemy query
        return []
    
    async def _query_pending_po_approvals(self) -> List[Dict]:
        """Query pending PO approvals"""
        return []
    
    async def _query_payment_dues(self) -> List[Dict]:
        """Query upcoming/overdue payments"""
        return []
    
    def _get_priority_level(self, score: int) -> str:
        """Convert numeric score to priority level"""
        if score >= 90:
            return "CRITICAL"
        elif score >= 75:
            return "URGENT"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        return "LOW"