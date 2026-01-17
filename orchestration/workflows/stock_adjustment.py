"""Stock adjustment workflow"""
from statemachine import State

from .base import ConversationWorkflow, StateDefinition


class StockAdjustmentWorkflow(ConversationWorkflow):
    """Inventory stock adjustment workflow"""
    
    workflow_type = "stock_adjustment"
    
    select_type = State(initial=True, value=StateDefinition(
        instruction_type="SELECT",
        prompt_template="What type of stock adjustment?",
        expected_input="adjustment_type",
        options=[
            {"value": "count", "label": "Physical Count"},
            {"value": "damage", "label": "Damage/Spoilage"},
            {"value": "correction", "label": "Correction"},
            {"value": "transfer", "label": "Transfer"}
        ]
    ))
    
    select_item = State(value=StateDefinition(
        instruction_type="SELECT",
        prompt_template="Select the item to adjust:",
        expected_input="item_id"
    ))
    
    show_current = State(value=StateDefinition(
        instruction_type="DISPLAY",
        prompt_template="Current stock for {item_name}:\n\n• System Quantity: {system_qty} {unit}\n• Last Count: {last_count_date}\n• Location: {location}",
        auto_advance=False
    ))
    
    enter_actual = State(value=StateDefinition(
        instruction_type="ASK",
        prompt_template="Enter the actual quantity counted:",
        expected_input="actual_quantity",
        validation={"type": "number", "min": 0}
    ))
    
    enter_reason = State(value=StateDefinition(
        instruction_type="ASK",
        prompt_template="Please provide a reason for this adjustment:",
        expected_input="reason",
        validation={"type": "required"}
    ))
    
    confirm = State(value=StateDefinition(
        instruction_type="CONFIRM",
        prompt_template="Adjustment Summary:\n\n• Item: {item_name}\n• From: {system_qty} → To: {actual_quantity}\n• Variance: {variance}\n• Reason: {reason}\n\nConfirm this adjustment?",
        expected_input="confirmation",
        options=[
            {"value": "confirm", "label": "Confirm"},
            {"value": "cancel", "label": "Cancel"}
        ]
    ))
    
    complete = State(final=True, value=StateDefinition(
        instruction_type="INFORM",
        prompt_template="Stock adjustment recorded.\n\nAdjustment ID: {adjustment_id}"
    ))
    
    cancelled = State(final=True, value=StateDefinition(
        instruction_type="INFORM",
        prompt_template="Adjustment cancelled."
    ))
    
    # Transitions
    type_selected = select_type.to(select_item)
    item_selected = select_item.to(show_current)
    proceed_to_entry = show_current.to(enter_actual)
    qty_entered = enter_actual.to(enter_reason)
    reason_entered = enter_reason.to(confirm)
    confirmed = confirm.to(complete, cond="user_confirmed")
    cancel = confirm.to(cancelled, unless="user_confirmed")
    
    def user_confirmed(self):
        return self.slot_values.get("confirmation") == "confirm"
    
    def get_completion_message(self) -> str:
        adj_id = self.context.get("adjustment_id", "N/A")
        return f"✅ Stock adjustment #{adj_id} has been recorded."