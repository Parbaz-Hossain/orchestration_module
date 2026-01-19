"""
Mock PO Creation Saga for Testing
Simulates the multi-step PO creation process without database.

Usage:
    from orchestration.mock.mock_po_saga import MockPOCreationSaga
    
    saga = MockPOCreationSaga()
    result = await saga.execute(context)
"""
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, field

from .static_data import get_mock_store, MockDataStore


@dataclass
class SagaStepResult:
    """Result of a saga step execution"""
    step_name: str
    status: str  # completed, failed, compensated
    result_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)


@dataclass 
class SagaResult:
    """Complete saga execution result"""
    saga_id: str
    status: str  # completed, failed, compensated
    steps: List[SagaStepResult] = field(default_factory=list)
    result_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class MockPOCreationSaga:
    """
    Mock implementation of PO Creation Saga.
    
    Steps:
    1. Update ReorderRequest status to 'processing'
    2. Create PurchaseOrder record
    3. Create ApprovalRequest if needed (based on threshold)
    4. Send notification to approver
    
    Each step can be compensated on failure.
    """
    
    def __init__(self, data_store: Optional[MockDataStore] = None):
        self.store = data_store or get_mock_store()
    
    async def execute(self, context: Dict[str, Any]) -> SagaResult:
        """
        Execute the complete PO creation saga.
        
        Required context fields:
        - user_id: int
        - organization_id: int
        - item_id: int
        - quantity: Decimal/float/str
        - supplier_id: int
        - unit_price: Decimal/float/str
        
        Optional:
        - reorder_request_id: int (if updating existing request)
        - notes: str
        """
        saga_id = str(uuid.uuid4())
        steps: List[SagaStepResult] = []
        result_data: Dict[str, Any] = {}
        
        try:
            # Step 1: Update Reorder Request
            step1 = await self._step_update_reorder_request(context)
            steps.append(step1)
            if step1.status == "failed":
                raise Exception(step1.error)
            result_data["reorder_request_id"] = step1.result_data.get("reorder_request_id")
            
            # Step 2: Create Purchase Order
            step2 = await self._step_create_purchase_order(context)
            steps.append(step2)
            if step2.status == "failed":
                raise Exception(step2.error)
            result_data["purchase_order_id"] = step2.result_data.get("purchase_order_id")
            result_data["po_number"] = step2.result_data.get("po_number")
            
            # Step 3: Check Approval and Create Request if needed
            approval_info = self._check_approval_required(context)
            result_data["approval_required"] = approval_info["required"]
            
            if approval_info["required"]:
                step3 = await self._step_create_approval_request(
                    context, 
                    result_data["purchase_order_id"],
                    approval_info
                )
                steps.append(step3)
                if step3.status == "failed":
                    raise Exception(step3.error)
                result_data["approval_request_id"] = step3.result_data.get("approval_request_id")
                result_data["approver_name"] = step3.result_data.get("approver_name")
                result_data["approver_id"] = step3.result_data.get("approver_id")
                result_data["po_status"] = "pending_approval"
            else:
                result_data["po_status"] = "approved"
            
            # Step 4: Send Notification
            if approval_info["required"]:
                step4 = await self._step_send_notification(context, result_data)
                steps.append(step4)
            
            return SagaResult(
                saga_id=saga_id,
                status="completed",
                steps=steps,
                result_data=result_data
            )
            
        except Exception as e:
            # Compensate completed steps in reverse order
            for step in reversed(steps):
                if step.status == "completed":
                    await self._compensate_step(step, context)
                    step.status = "compensated"
            
            return SagaResult(
                saga_id=saga_id,
                status="failed",
                steps=steps,
                result_data=result_data,
                error=str(e)
            )
    
    # -------------------------------------------------------------------------
    # Saga Steps
    # -------------------------------------------------------------------------
    
    async def _step_update_reorder_request(self, context: Dict[str, Any]) -> SagaStepResult:
        """Step 1: Update reorder request status"""
        try:
            reorder_id = context.get("reorder_request_id")
            
            if reorder_id:
                self.store.update_reorder_request(reorder_id, {
                    "status": "processing",
                    "actioned_by": context["user_id"],
                })
            
            return SagaStepResult(
                step_name="update_reorder_request",
                status="completed",
                result_data={"reorder_request_id": reorder_id}
            )
        except Exception as e:
            return SagaStepResult(
                step_name="update_reorder_request",
                status="failed",
                error=str(e)
            )
    
    async def _step_create_purchase_order(self, context: Dict[str, Any]) -> SagaStepResult:
        """Step 2: Create purchase order"""
        try:
            quantity = Decimal(str(context["quantity"]))
            unit_price = Decimal(str(context["unit_price"]))
            total_amount = quantity * unit_price
            
            # Generate PO number
            po_number = self.store.generate_po_number()
            
            # Get supplier for expected delivery calculation
            supplier = self.store.get_supplier(context["supplier_id"])
            lead_time = supplier.lead_time_days if supplier else 3
            expected_delivery = datetime.now() + timedelta(days=lead_time)
            
            # Create PO
            po = self.store.create_purchase_order({
                "organization_id": context["organization_id"],
                "supplier_id": context["supplier_id"],
                "po_number": po_number,
                "status": "draft",
                "total_amount": total_amount,
                "created_by": context["user_id"],
                "items_count": 1,
            })
            
            return SagaStepResult(
                step_name="create_purchase_order",
                status="completed",
                result_data={
                    "purchase_order_id": po.id,
                    "po_number": po_number,
                    "total_amount": str(total_amount),
                    "expected_delivery": expected_delivery.strftime("%b %d, %Y"),
                }
            )
        except Exception as e:
            return SagaStepResult(
                step_name="create_purchase_order",
                status="failed",
                error=str(e)
            )
    
    async def _step_create_approval_request(
        self, 
        context: Dict[str, Any],
        po_id: int,
        approval_info: Dict[str, Any]
    ) -> SagaStepResult:
        """Step 3: Create approval request"""
        try:
            quantity = Decimal(str(context["quantity"]))
            unit_price = Decimal(str(context["unit_price"]))
            total_amount = quantity * unit_price
            
            approval = self.store.create_approval_request({
                "organization_id": context["organization_id"],
                "entity_type": "purchase_order",
                "entity_id": po_id,
                "amount": total_amount,
                "requester_id": context["user_id"],
                "approver_id": approval_info["approver_id"],
            })
            
            approver = self.store.get_user(approval_info["approver_id"])
            
            return SagaStepResult(
                step_name="create_approval_request",
                status="completed",
                result_data={
                    "approval_request_id": approval.id,
                    "approver_id": approval_info["approver_id"],
                    "approver_name": approver.full_name if approver else "Unknown",
                }
            )
        except Exception as e:
            return SagaStepResult(
                step_name="create_approval_request",
                status="failed",
                error=str(e)
            )
    
    async def _step_send_notification(
        self, 
        context: Dict[str, Any],
        result_data: Dict[str, Any]
    ) -> SagaStepResult:
        """Step 4: Send notification to approver"""
        # In mock, we just log the notification
        print(f"📧 [NOTIFICATION] PO #{result_data['po_number']} requires approval")
        print(f"   → Sent to: {result_data.get('approver_name', 'Unknown')}")
        
        return SagaStepResult(
            step_name="send_notification",
            status="completed",
            result_data={"notification_sent": True}
        )
    
    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    
    def _check_approval_required(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if approval is required based on amount threshold"""
        quantity = Decimal(str(context["quantity"]))
        unit_price = Decimal(str(context["unit_price"]))
        total_amount = quantity * unit_price
        
        # Default threshold: $100
        org = self.store.get_organization(context["organization_id"])
        threshold = Decimal(str(org.settings.get("po_approval_threshold", 100))) if org else Decimal("100")
        
        if total_amount <= threshold:
            return {"required": False}
        
        # Find store manager for approval
        approver = self.store.get_store_manager(context["organization_id"])
        
        if approver:
            return {
                "required": True,
                "approver_id": approver.id,
                "approver_name": approver.full_name,
                "threshold": str(threshold),
                "amount": str(total_amount),
            }
        
        return {"required": False}
    
    async def _compensate_step(self, step: SagaStepResult, context: Dict[str, Any]) -> None:
        """Compensate a completed step"""
        if step.step_name == "update_reorder_request":
            reorder_id = step.result_data.get("reorder_request_id")
            if reorder_id:
                self.store.update_reorder_request(reorder_id, {"status": "pending"})
                print(f"↩️ Compensated: Reverted reorder request #{reorder_id} to pending")
        
        elif step.step_name == "create_purchase_order":
            po_id = step.result_data.get("purchase_order_id")
            if po_id and po_id in self.store.purchase_orders:
                self.store.purchase_orders[po_id].status = "cancelled"
                print(f"↩️ Compensated: Cancelled PO #{step.result_data.get('po_number')}")
        
        elif step.step_name == "create_approval_request":
            approval_id = step.result_data.get("approval_request_id")
            if approval_id and approval_id in self.store.approval_requests:
                self.store.approval_requests[approval_id].status = "cancelled"
                print(f"↩️ Compensated: Cancelled approval request #{approval_id}")