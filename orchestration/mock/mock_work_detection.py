"""
Mock Work Detection Service for Testing Orchestration Module
Uses static data instead of database queries.

Usage:
    from orchestration.mock.mock_work_detection import MockWorkDetectionService
    
    detector = MockWorkDetectionService()
    tasks = await detector.get_prioritized_work(user_id=2, role="purchase_manager")
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

# Import from static_data.py (adjust path based on your project structure)
from .static_data import get_mock_store, MockDataStore


class MockWorkDetectionService:
    """
    Mock implementation of WorkDetectionService using static data.
    No database connection required - perfect for testing orchestration logic.
    """
    
    def __init__(self, data_store: Optional[MockDataStore] = None):
        self.store = data_store or get_mock_store()
    
    async def get_prioritized_work(
        self, 
        user_id: int, 
        role: str,
        organization_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all pending work for a role, calculate priorities and sort.
        This is the main entry point called by the orchestrator.
        """
        
        # Get user's organization if not provided
        if not organization_id:
            organization_id = self.store.get_user_organization(user_id)
        
        if not organization_id:
            return []
        
        # Route to role-specific detector
        role_detectors = {
            "purchase_manager": self._get_purchase_manager_work,
            "store_manager": self._get_store_manager_work,
            "inventory_manager": self._get_inventory_manager_work,
            "hr_manager": self._get_hr_manager_work,
            "supervisor": self._get_supervisor_work,
        }
        
        detector = role_detectors.get(role, self._get_default_work)
        tasks = await detector(user_id, organization_id)
        
        # Calculate priorities and sort
        for task in tasks:
            task["calculated_priority"] = self._calculate_priority(task)
            task["priority_level"] = self._get_priority_level(task["calculated_priority"])
        
        return sorted(tasks, key=lambda x: x["calculated_priority"], reverse=True)
    
    # -------------------------------------------------------------------------
    # Role-Specific Work Detection
    # -------------------------------------------------------------------------
    
    async def _get_purchase_manager_work(
        self, 
        user_id: int, 
        organization_id: int
    ) -> List[Dict]:
        """Get pending work for purchase manager"""
        tasks = []
        
        # 1. Low stock alerts (items below reorder level)
        low_stock_items = self.store.get_low_stock_items(organization_id)
        for item in low_stock_items:
            supplier_info = self.store.get_preferred_supplier(item["id"])
            last_order = self.store.get_last_order_info(item["id"])
            
            # Calculate estimated order value
            unit_price = supplier_info["unit_price"] if supplier_info else item["cost_price"]
            estimated_total = Decimal(str(item["reorder_quantity"])) * Decimal(str(unit_price))
            
            tasks.append({
                "task_type": "low_stock_reorder",
                "reference_id": item["id"],
                "reference_table": "items",
                "title": f"Reorder: {item['name']}",
                "description": f"Current: {item['current_stock']} {item['unit_symbol']} | Reorder Level: {item['reorder_level']}",
                "days_until_stockout": item["days_until_stockout"],
                "value_amount": float(estimated_total),
                "created_at": datetime.now(),
                
                # Context for workflow
                "item_id": item["id"],
                "item_name": item["name"],
                "item_code": item["code"],
                "current_stock": str(item["current_stock"]),
                "unit": item["unit_symbol"],
                "reorder_level": str(item["reorder_level"]),
                "reorder_quantity": str(item["reorder_quantity"]),
                "suggested_quantity": str(item["reorder_quantity"]),
                "supplier_id": supplier_info["supplier_id"] if supplier_info else None,
                "supplier_name": supplier_info["supplier_name"] if supplier_info else "No preferred supplier",
                "unit_price": str(supplier_info["unit_price"]) if supplier_info else str(item["cost_price"]),
                "last_order_qty": last_order["quantity"] if last_order else None,
                "last_order_price": last_order["unit_price"] if last_order else None,
                "last_order_date": last_order["order_date"] if last_order else None,
                "last_order_supplier": last_order["supplier_name"] if last_order else None,
                "estimated_total": str(estimated_total),
            })
        
        # 2. Pending PO approvals (if user can approve)
        pending_pos = self.store.get_pending_po_approvals(organization_id)
        for po in pending_pos:
            tasks.append({
                "task_type": "po_approval",
                "reference_id": po["id"],
                "reference_table": "purchase_orders",
                "title": f"Approve PO #{po['po_number']}",
                "description": f"Supplier: {po['supplier_name']} | Amount: ${po['total_amount']}",
                "days_pending": po["days_pending"],
                "value_amount": float(po["total_amount"]),
                "created_at": po["created_at"],
                
                # Context
                "po_number": po["po_number"],
                "supplier_name": po["supplier_name"],
                "total_amount": str(po["total_amount"]),
                "requested_by": po["requested_by_name"],
                "items_count": po["items_count"],
            })
        
        # 3. Supplier payment dues
        payment_dues = self.store.get_payment_dues(organization_id)
        for payment in payment_dues:
            days_until_due = (payment["due_date"] - datetime.now()).days
            
            tasks.append({
                "task_type": "supplier_payment",
                "reference_id": payment["id"],
                "reference_table": "supplier_payments",
                "title": f"Payment due: {payment['supplier_name']}",
                "description": f"Amount: ${payment['amount']} | Due: {payment['due_date'].strftime('%b %d')}",
                "deadline": payment["due_date"],
                "value_amount": float(payment["amount"]),
                "created_at": payment["created_at"],
                
                # Context
                "supplier_name": payment["supplier_name"],
                "invoice_number": payment["invoice_number"],
                "amount": str(payment["amount"]),
                "days_until_due": days_until_due,
                "is_overdue": days_until_due < 0,
            })
        
        return tasks
    
    async def _get_store_manager_work(
        self, 
        user_id: int, 
        organization_id: int
    ) -> List[Dict]:
        """Get pending work for store manager - aggregates from all departments"""
        tasks = []
        
        # Get all tasks from purchase manager
        tasks.extend(await self._get_purchase_manager_work(user_id, organization_id))
        
        # Add specific approval tasks assigned to this user
        approvals = self.store.get_pending_approvals_for_user(user_id)
        for approval in approvals:
            tasks.append({
                "task_type": f"{approval['entity_type']}_approval",
                "reference_id": approval["id"],
                "reference_table": "approval_requests",
                "title": f"Approve: {approval['title']}",
                "description": f"Requested by {approval['requester_name']} | ${approval['amount']}",
                "days_pending": approval["days_pending"],
                "value_amount": float(approval["amount"]),
                "created_at": datetime.now(),
            })
        
        return tasks
    
    async def _get_inventory_manager_work(
        self, 
        user_id: int, 
        organization_id: int
    ) -> List[Dict]:
        """Get pending work for inventory manager"""
        tasks = []
        
        # Low stock items (for awareness, not for ordering)
        low_stock = self.store.get_low_stock_items(organization_id)
        for item in low_stock:
            tasks.append({
                "task_type": "stock_alert",
                "reference_id": item["id"],
                "reference_table": "items",
                "title": f"Low Stock Alert: {item['name']}",
                "description": f"Current: {item['current_stock']} {item['unit_symbol']}",
                "days_until_stockout": item["days_until_stockout"],
                "value_amount": 0,
                "created_at": datetime.now(),
            })
        
        return tasks
    
    async def _get_hr_manager_work(
        self, 
        user_id: int, 
        organization_id: int
    ) -> List[Dict]:
        """Get pending work for HR manager"""
        # In a real system, this would include:
        # - Leave requests pending approval
        # - Attendance exceptions
        # - Shift assignments needed
        return []
    
    async def _get_supervisor_work(
        self, 
        user_id: int, 
        organization_id: int
    ) -> List[Dict]:
        """Get pending work for supervisor"""
        # Limited view - just alerts
        tasks = []
        
        # Critical stock alerts only
        low_stock = self.store.get_low_stock_items(organization_id)
        for item in low_stock:
            if item["days_until_stockout"] <= 3:  # Only critical items
                tasks.append({
                    "task_type": "stock_alert",
                    "reference_id": item["id"],
                    "reference_table": "items",
                    "title": f"⚠️ Critical: {item['name']}",
                    "description": f"Only {item['days_until_stockout']} days of stock remaining",
                    "days_until_stockout": item["days_until_stockout"],
                    "value_amount": 0,
                    "created_at": datetime.now(),
                })
        
        return tasks
    
    async def _get_default_work(
        self, 
        user_id: int, 
        organization_id: int
    ) -> List[Dict]:
        """Default work detection for unknown roles"""
        return []
    
    # -------------------------------------------------------------------------
    # Priority Calculation
    # -------------------------------------------------------------------------
    
    def _calculate_priority(self, task: Dict[str, Any]) -> int:
        """
        Calculate priority score (0-100) based on multiple factors.
        Higher score = higher priority.
        """
        score = 50  # Base score
        
        task_type = task.get("task_type", "")
        
        # Factor 1: Urgency (days until stockout or deadline)
        if "days_until_stockout" in task:
            days = task["days_until_stockout"]
            if days <= 2:
                score += 40  # Critical
            elif days <= 5:
                score += 25  # Urgent
            elif days <= 7:
                score += 15  # High
            else:
                score += 5   # Medium
        
        # Factor 2: Days pending (for approvals)
        if "days_pending" in task:
            days = task["days_pending"]
            if days >= 7:
                score += 20
            elif days >= 3:
                score += 10
            elif days >= 1:
                score += 5
        
        # Factor 3: Financial value
        value = task.get("value_amount", 0)
        if value > 500:
            score += 10
        elif value > 200:
            score += 5
        elif value > 100:
            score += 3
        
        # Factor 4: Task type importance
        type_weights = {
            "low_stock_reorder": 10,
            "po_approval": 8,
            "supplier_payment": 6,
            "stock_alert": 4,
        }
        score += type_weights.get(task_type, 0)
        
        # Factor 5: Overdue penalty/boost
        if task.get("is_overdue"):
            score += 15
        
        # Ensure score is within bounds
        return min(100, max(0, score))
    
    def _get_priority_level(self, score: int) -> str:
        """Convert numeric score to priority level label"""
        if score >= 90:
            return "CRITICAL"
        elif score >= 75:
            return "URGENT"
        elif score >= 60:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        return "LOW"


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

async def get_purchase_manager_tasks(user_id: int = 2) -> List[Dict[str, Any]]:
    """
    Convenience function to quickly get Purchase Manager tasks.
    
    Usage:
        tasks = await get_purchase_manager_tasks()
        for task in tasks:
            print(f"{task['priority_level']}: {task['title']}")
    """
    detector = MockWorkDetectionService()
    return await detector.get_prioritized_work(user_id=user_id, role="purchase_manager")