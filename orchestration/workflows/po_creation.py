"""Purchase Order creation workflow"""
from statemachine import State

from .base import ConversationWorkflow, StateDefinition


class POCreationWorkflow(ConversationWorkflow):
    """Purchase Order creation workflow state machine"""
    
    workflow_type = "po_creation"
    
    # Define states with AI instructions
    greeting = State(initial=True, value=StateDefinition(
        instruction_type="DISPLAY",
        prompt_template="Let me help you create a purchase order.\n\nItem: {title}\nCurrent Stock: {current_stock}\n\nBased on your history, I suggest ordering from the usual supplier.",
        auto_advance=False
    ))
    
    confirm_suggestion = State(value=StateDefinition(
        instruction_type="CONFIRM",
        prompt_template="Would you like to proceed with a reorder based on your last order?",
        expected_input="use_suggestions",
        options=[
            {"value": "yes", "label": "Yes, use last order details"},
            {"value": "modify", "label": "Modify details"},
            {"value": "cancel", "label": "Cancel"}
        ]
    ))
    
    select_supplier = State(value=StateDefinition(
        instruction_type="SELECT",
        prompt_template="Which supplier would you like to order from?",
        expected_input="supplier_id"
    ))
    
    specify_quantity = State(value=StateDefinition(
        instruction_type="ASK",
        prompt_template="How much would you like to order?\n\nSuggested quantity: {suggested_quantity} based on average usage.",
        expected_input="quantity",
        validation={"type": "number", "min": 1, "max": 10000}
    ))
    
    review_order = State(value=StateDefinition(
        instruction_type="CONFIRM",
        prompt_template="Order Summary:\n\n• Item: {item_name}\n• Quantity: {quantity}\n• Supplier: {supplier_name}\n• Estimated Total: ${estimated_total}\n\nConfirm this order?",
        expected_input="confirmation",
        options=[
            {"value": "confirm", "label": "Confirm & Submit"},
            {"value": "edit", "label": "Edit Order"},
            {"value": "cancel", "label": "Cancel"}
        ]
    ))
    
    processing = State(value=StateDefinition(
        instruction_type="INFORM",
        prompt_template="Creating your purchase order...",
        auto_advance=True
    ))
    
    approval_pending = State(value=StateDefinition(
        instruction_type="INFORM",
        prompt_template="Purchase Order #{po_number} has been created and submitted for approval.\n\nApprover: {approver_name}\nExpected response: Within 24 hours"
    ))
    
    complete = State(final=True, value=StateDefinition(
        instruction_type="INFORM",
        prompt_template="Purchase Order #{po_number} has been created successfully!"
    ))
    
    cancelled = State(final=True, value=StateDefinition(
        instruction_type="INFORM",
        prompt_template="Order cancelled."
    ))
    
    # Transitions
    start = greeting.to(confirm_suggestion)
    accept_suggestion = confirm_suggestion.to(specify_quantity, cond="suggestions_accepted")
    modify_order = confirm_suggestion.to(select_supplier, cond="wants_modify")
    cancel_from_suggestion = confirm_suggestion.to(cancelled, cond="user_cancelled")
    
    supplier_selected = select_supplier.to(specify_quantity)
    quantity_set = specify_quantity.to(review_order)
    
    confirm_order = review_order.to(processing, cond="user_confirmed")
    edit_order = review_order.to(select_supplier, cond="wants_edit")
    cancel_from_review = review_order.to(cancelled, cond="user_cancelled")
    
    process_to_approval = processing.to(approval_pending, cond="approval_needed")
    process_to_complete = processing.to(complete, unless="approval_needed")
    
    approval_done = approval_pending.to(complete)
    
    # Guards
    def suggestions_accepted(self):
        return self.slot_values.get("use_suggestions") == "yes"
    
    def wants_modify(self):
        return self.slot_values.get("use_suggestions") == "modify"
    
    def user_confirmed(self):
        return self.slot_values.get("confirmation") == "confirm"
    
    def wants_edit(self):
        return self.slot_values.get("confirmation") == "edit"
    
    def user_cancelled(self):
        val = self.slot_values.get("use_suggestions") or self.slot_values.get("confirmation")
        return val == "cancel"
    
    def approval_needed(self):
        return self.context.get("approval_required", False)
    
    def get_completion_message(self) -> str:
        po_number = self.context.get("po_number", "N/A")
        return f"✅ Purchase Order #{po_number} has been created successfully!"