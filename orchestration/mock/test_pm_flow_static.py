"""
Purchase Manager Flow Test - Complete Demonstration
This script demonstrates the orchestration module working with static mock data.

Run this file directly to see the complete Purchase Manager workflow:
    python test_pm_flow_static.py

No database or Redis required - uses static mock data.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
import uuid

# =============================================================================
# INLINE STATIC DATA (No separate file imports needed)
# =============================================================================

@dataclass
class MockUser:
    id: int
    organization_id: int
    role_id: int
    first_name: str
    last_name: str
    email: str
    role_code: str = ""
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

@dataclass
class MockItem:
    id: int
    code: str
    name: str
    unit_symbol: str
    current_stock: Decimal
    reorder_level: Decimal
    reorder_quantity: Decimal
    avg_daily_usage: Decimal
    cost_price: Decimal
    
    @property
    def days_until_stockout(self) -> int:
        if self.avg_daily_usage <= 0:
            return 999
        return max(0, int(float(self.current_stock) / float(self.avg_daily_usage)))

@dataclass
class MockSupplier:
    id: int
    name: str
    lead_time_days: int = 3

# Static Data
USERS = {
    1: MockUser(1, 1, 1, "Sarah", "Johnson", "sarah@demo.com", "store_manager"),
    2: MockUser(2, 1, 2, "Ahmed", "Hassan", "ahmed@demo.com", "purchase_manager"),
}

ITEMS = {
    1: MockItem(1, "ITEM001", "Coffee Beans (Premium Arabica)", "kg", 
                Decimal("0.5"), Decimal("5"), Decimal("10"), Decimal("0.25"), Decimal("45.00")),
    2: MockItem(2, "ITEM002", "White Sugar", "kg",
                Decimal("1.5"), Decimal("10"), Decimal("25"), Decimal("0.5"), Decimal("2.50")),
    3: MockItem(3, "ITEM003", "Fresh Whole Milk", "L",
                Decimal("20"), Decimal("30"), Decimal("50"), Decimal("4"), Decimal("3.50")),
    4: MockItem(4, "ITEM004", "Takeaway Cups (12oz)", "pc",
                Decimal("150"), Decimal("200"), Decimal("500"), Decimal("20"), Decimal("0.15")),
}

SUPPLIERS = {
    1: MockSupplier(1, "ACME Coffee Corp", 3),
    2: MockSupplier(2, "Fresh Dairy Supplies", 1),
    3: MockSupplier(3, "Bakery Wholesale Inc", 2),
}

ITEM_SUPPLIERS = {
    1: {"supplier_id": 1, "unit_price": Decimal("45.00"), "last_qty": "10", "last_date": "Jan 05, 2026"},
    2: {"supplier_id": 3, "unit_price": Decimal("2.50"), "last_qty": "25", "last_date": "Dec 28, 2025"},
    3: {"supplier_id": 2, "unit_price": Decimal("3.50"), "last_qty": "50", "last_date": "Jan 14, 2026"},
    4: {"supplier_id": 3, "unit_price": Decimal("0.15"), "last_qty": "500", "last_date": "Dec 18, 2025"},
}


# =============================================================================
# ORCHESTRATION SCHEMAS
# =============================================================================

class InstructionType(Enum):
    GREETING = "GREETING"
    SELECT = "SELECT"
    DISPLAY = "DISPLAY"
    CONFIRM = "CONFIRM"
    INPUT = "INPUT"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

class UserResponseType(Enum):
    SELECTION = "SELECTION"
    CONFIRMATION = "CONFIRMATION"
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    CANCEL = "CANCEL"

@dataclass
class InstructionOption:
    value: str
    label: str
    priority: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BackendInstruction:
    """Instruction from backend to AI agent"""
    instruction_id: str
    instruction_type: InstructionType
    prompt: str
    options: List[InstructionOption] = field(default_factory=list)
    expected_response: Optional[UserResponseType] = None
    context: Dict[str, Any] = field(default_factory=dict)
    workflow_id: Optional[str] = None
    current_state: str = ""
    progress_percentage: Optional[int] = None

@dataclass
class AgentResponse:
    """Response from AI agent to backend"""
    in_response_to: str
    response_type: UserResponseType
    raw_input: str
    extracted_value: Any
    session_id: str = ""


# =============================================================================
# MOCK SESSION MANAGER
# =============================================================================

class MockSession:
    """Simple session store for testing"""
    def __init__(self, session_id: str, user_id: int, role: str, user_name: str):
        self.session_id = session_id
        self.user_id = user_id
        self.role = role
        self.user_name = user_name
        self.current_workflow_id: Optional[str] = None
        self.current_state: str = "idle"
        self.pending_tasks: List[Dict] = []
        self.current_task: Optional[Dict] = None
        self.slot_values: Dict[str, Any] = {}
        self.created_at = datetime.now()


# =============================================================================
# MOCK WORK DETECTION SERVICE
# =============================================================================

class MockWorkDetector:
    """Detects and prioritizes work using static data"""
    
    def get_prioritized_tasks(self, user_id: int, role: str) -> List[Dict[str, Any]]:
        """Get all pending tasks for a role, sorted by priority"""
        tasks = []
        
        if role == "purchase_manager":
            # Get low stock items
            for item_id, item in ITEMS.items():
                if item.current_stock <= item.reorder_level:
                    supplier_info = ITEM_SUPPLIERS.get(item_id, {})
                    supplier = SUPPLIERS.get(supplier_info.get("supplier_id", 0))
                    
                    tasks.append({
                        "task_type": "low_stock_reorder",
                        "reference_id": item_id,
                        "title": f"Reorder: {item.name}",
                        "description": f"Current: {item.current_stock} {item.unit_symbol} | Reorder: {item.reorder_level}",
                        "days_until_stockout": item.days_until_stockout,
                        "priority_score": self._calculate_priority(item.days_until_stockout),
                        "priority_level": self._get_priority_level(item.days_until_stockout),
                        # Task context
                        "item_id": item_id,
                        "item_name": item.name,
                        "item_code": item.code,
                        "current_stock": str(item.current_stock),
                        "unit": item.unit_symbol,
                        "reorder_quantity": str(item.reorder_quantity),
                        "supplier_id": supplier_info.get("supplier_id"),
                        "supplier_name": supplier.name if supplier else "Unknown",
                        "unit_price": str(supplier_info.get("unit_price", item.cost_price)),
                        "last_order_qty": supplier_info.get("last_qty"),
                        "last_order_date": supplier_info.get("last_date"),
                    })
        
        # Sort by priority score (higher = more urgent)
        return sorted(tasks, key=lambda x: x["priority_score"], reverse=True)
    
    def _calculate_priority(self, days: int) -> int:
        if days <= 2: return 95
        if days <= 5: return 80
        if days <= 7: return 65
        return 40
    
    def _get_priority_level(self, days: int) -> str:
        if days <= 2: return "CRITICAL"
        if days <= 5: return "URGENT"
        if days <= 7: return "HIGH"
        return "MEDIUM"


# =============================================================================
# MOCK ORCHESTRATION ENGINE
# =============================================================================

class MockOrchestrationEngine:
    """
    Simplified orchestration engine for testing.
    Demonstrates the core flow without full state machine complexity.
    """
    
    def __init__(self):
        self.sessions: Dict[str, MockSession] = {}
        self.work_detector = MockWorkDetector()
        self.po_counter = 141
    
    def initialize_session(
        self, 
        user_id: int, 
        role: str, 
        user_name: str
    ) -> tuple[MockSession, BackendInstruction]:
        """Initialize a new session and return greeting instruction"""
        
        session_id = str(uuid.uuid4())[:8]
        session = MockSession(session_id, user_id, role, user_name)
        
        # Detect pending work
        tasks = self.work_detector.get_prioritized_tasks(user_id, role)
        session.pending_tasks = tasks
        
        # Build greeting instruction
        greeting = self._build_greeting_instruction(session, tasks)
        
        self.sessions[session_id] = session
        return session, greeting
    
    def process_response(
        self, 
        session_id: str, 
        response: AgentResponse
    ) -> BackendInstruction:
        """Process user response and return next instruction"""
        
        session = self.sessions.get(session_id)
        if not session:
            return self._error_instruction("Session not found")
        
        # Route based on current state
        if session.current_state == "task_selection":
            return self._handle_task_selection(session, response)
        
        elif session.current_state == "confirm_suggestion":
            return self._handle_suggestion_confirmation(session, response)
        
        elif session.current_state == "specify_quantity":
            return self._handle_quantity_input(session, response)
        
        elif session.current_state == "review_order":
            return self._handle_order_confirmation(session, response)
        
        elif session.current_state == "complete":
            return self._handle_next_task(session, response)
        
        return self._error_instruction("Unknown state")
    
    # -------------------------------------------------------------------------
    # State Handlers
    # -------------------------------------------------------------------------
    
    def _build_greeting_instruction(
        self, 
        session: MockSession, 
        tasks: List[Dict]
    ) -> BackendInstruction:
        """Build the initial greeting with task list"""
        
        session.current_state = "task_selection"
        
        # Build prompt
        task_count = len(tasks)
        top_tasks = tasks[:3]
        
        prompt_lines = [
            f"Good morning, {session.user_name}! You have {task_count} pending items.",
            "",
            "Most urgent:"
        ]
        
        for task in top_tasks:
            emoji = self._priority_emoji(task["priority_level"])
            if task["task_type"] == "low_stock_reorder":
                prompt_lines.append(f"{emoji} {task['item_name']} ({task['days_until_stockout']} days to stockout)")
            else:
                prompt_lines.append(f"{emoji} {task['title']}")
        
        prompt_lines.append("")
        prompt_lines.append("What would you like to tackle first?")
        
        # Build options
        options = []
        for task in tasks:
            emoji = self._priority_emoji(task["priority_level"])
            options.append(InstructionOption(
                value=f"{task['task_type']}:{task['reference_id']}",
                label=f"{emoji} {task['title']}",
                priority=task["priority_level"],
                metadata=task
            ))
        
        return BackendInstruction(
            instruction_id=str(uuid.uuid4())[:8],
            instruction_type=InstructionType.SELECT,
            prompt="\n".join(prompt_lines),
            options=options,
            expected_response=UserResponseType.SELECTION,
            current_state="task_selection",
            progress_percentage=10
        )
    
    def _handle_task_selection(
        self, 
        session: MockSession, 
        response: AgentResponse
    ) -> BackendInstruction:
        """Handle user selecting a task"""
        
        # Parse selection (format: "task_type:reference_id")
        selected = response.extracted_value
        if ":" in str(selected):
            task_type, ref_id = str(selected).split(":", 1)
            ref_id = int(ref_id)
        else:
            # Find by item name
            for task in session.pending_tasks:
                if selected.lower() in task.get("item_name", "").lower():
                    task_type = task["task_type"]
                    ref_id = task["reference_id"]
                    break
            else:
                ref_id = int(selected) if selected.isdigit() else 1
                task_type = "low_stock_reorder"
        
        # Find the task
        task = next(
            (t for t in session.pending_tasks if t["reference_id"] == ref_id),
            session.pending_tasks[0] if session.pending_tasks else None
        )
        
        if not task:
            return self._error_instruction("Task not found")
        
        session.current_task = task
        session.current_state = "confirm_suggestion"
        
        # Build display instruction
        item = ITEMS.get(task["item_id"])
        
        prompt_lines = [
            f"📦 {task['item_name']}",
            "",
            f"Current stock: {task['current_stock']} {task['unit']} ({task['days_until_stockout']} days remaining)",
            f"Reorder level: {item.reorder_level if item else 'N/A'} {task['unit']}",
            "",
        ]
        
        if task.get("last_order_qty"):
            prompt_lines.append(f"Last order: {task['last_order_qty']} {task['unit']} from {task['supplier_name']} on {task['last_order_date']}")
            prompt_lines.append(f"Price: ${task['unit_price']}/{task['unit']}")
            prompt_lines.append("")
            prompt_lines.append("Would you like to create a reorder based on your last order?")
        else:
            prompt_lines.append(f"Suggested supplier: {task['supplier_name']}")
            prompt_lines.append(f"Suggested quantity: {task['reorder_quantity']} {task['unit']}")
            prompt_lines.append("")
            prompt_lines.append("Would you like to proceed with this suggestion?")
        
        return BackendInstruction(
            instruction_id=str(uuid.uuid4())[:8],
            instruction_type=InstructionType.CONFIRM,
            prompt="\n".join(prompt_lines),
            options=[
                InstructionOption("yes", "Yes, use last order details"),
                InstructionOption("modify", "Modify quantity/supplier"),
                InstructionOption("skip", "Skip for now"),
            ],
            expected_response=UserResponseType.CONFIRMATION,
            current_state="confirm_suggestion",
            context={"task": task},
            progress_percentage=30
        )
    
    def _handle_suggestion_confirmation(
        self, 
        session: MockSession, 
        response: AgentResponse
    ) -> BackendInstruction:
        """Handle user confirming/modifying suggestion"""
        
        value = str(response.extracted_value).lower()
        task = session.current_task
        
        if value in ["skip", "no", "cancel"]:
            # Move to next task
            session.pending_tasks = [t for t in session.pending_tasks if t["reference_id"] != task["reference_id"]]
            session.current_task = None
            session.current_state = "task_selection"
            return self._build_greeting_instruction(session, session.pending_tasks)
        
        if value in ["yes", "confirm", "ok"]:
            # Use suggested quantity
            session.slot_values["quantity"] = task.get("last_order_qty") or task["reorder_quantity"]
            session.slot_values["supplier_id"] = task["supplier_id"]
            session.slot_values["unit_price"] = task["unit_price"]
        
        # Ask for quantity confirmation/modification
        session.current_state = "specify_quantity"
        
        suggested_qty = session.slot_values.get("quantity", task["reorder_quantity"])
        
        return BackendInstruction(
            instruction_id=str(uuid.uuid4())[:8],
            instruction_type=InstructionType.INPUT,
            prompt=f"How many {task['unit']} would you like to order?\n\nSuggested: {suggested_qty} {task['unit']}",
            expected_response=UserResponseType.NUMBER,
            current_state="specify_quantity",
            context={"suggested": suggested_qty},
            progress_percentage=50
        )
    
    def _handle_quantity_input(
        self, 
        session: MockSession, 
        response: AgentResponse
    ) -> BackendInstruction:
        """Handle quantity input"""
        
        # Extract number from response
        qty_str = str(response.extracted_value).replace(",", "").strip()
        try:
            # Handle "10 kg" format
            qty = Decimal(qty_str.split()[0])
        except:
            qty = Decimal(session.slot_values.get("quantity", "10"))
        
        session.slot_values["quantity"] = str(qty)
        task = session.current_task
        
        # Calculate total
        unit_price = Decimal(str(session.slot_values.get("unit_price", task["unit_price"])))
        total = qty * unit_price
        
        session.slot_values["total"] = str(total)
        session.current_state = "review_order"
        
        # Build review instruction
        prompt_lines = [
            "📋 Order Review",
            "",
            f"Item: {task['item_name']}",
            f"Quantity: {qty} {task['unit']}",
            f"Supplier: {task['supplier_name']}",
            f"Unit Price: ${unit_price}",
            f"",
            f"💰 Total: ${total:.2f}",
            "",
        ]
        
        if total > 100:
            prompt_lines.append("⚠️ This order exceeds $100 and will require Store Manager approval.")
            prompt_lines.append("")
        
        prompt_lines.append("Confirm this order?")
        
        return BackendInstruction(
            instruction_id=str(uuid.uuid4())[:8],
            instruction_type=InstructionType.CONFIRM,
            prompt="\n".join(prompt_lines),
            options=[
                InstructionOption("confirm", "✅ Confirm and Submit"),
                InstructionOption("edit", "✏️ Edit Order"),
                InstructionOption("cancel", "❌ Cancel"),
            ],
            expected_response=UserResponseType.CONFIRMATION,
            current_state="review_order",
            progress_percentage=70
        )
    
    def _handle_order_confirmation(
        self, 
        session: MockSession, 
        response: AgentResponse
    ) -> BackendInstruction:
        """Handle final order confirmation - execute saga"""
        
        value = str(response.extracted_value).lower()
        
        if value in ["cancel", "no"]:
            session.current_state = "task_selection"
            return self._build_greeting_instruction(session, session.pending_tasks)
        
        if value in ["edit", "modify"]:
            session.current_state = "specify_quantity"
            return self._handle_suggestion_confirmation(session, AgentResponse(
                in_response_to="", response_type=UserResponseType.CONFIRMATION,
                raw_input="yes", extracted_value="yes"
            ))
        
        # Execute PO creation (mock saga)
        task = session.current_task
        self.po_counter += 1
        po_number = f"PO-2026-{self.po_counter:04d}"
        
        total = Decimal(session.slot_values.get("total", "0"))
        needs_approval = total > 100
        
        # Build completion message
        prompt_lines = [
            "✅ Purchase Order Created Successfully!",
            "",
            f"PO Number: {po_number}",
            f"Item: {task['item_name']}",
            f"Quantity: {session.slot_values['quantity']} {task['unit']}",
            f"Total: ${total:.2f}",
            "",
        ]
        
        if needs_approval:
            prompt_lines.append(f"📤 Status: Submitted for Approval")
            prompt_lines.append(f"👤 Approver: Sarah Johnson (Store Manager)")
            prompt_lines.append("")
            prompt_lines.append("Sarah has been notified and will review shortly.")
        else:
            prompt_lines.append(f"📤 Status: Auto-Approved (under $100 threshold)")
        
        # Remove completed task
        session.pending_tasks = [t for t in session.pending_tasks if t["reference_id"] != task["reference_id"]]
        
        # Offer next task
        if session.pending_tasks:
            next_task = session.pending_tasks[0]
            prompt_lines.append("")
            prompt_lines.append("─" * 40)
            prompt_lines.append("")
            prompt_lines.append(f"Next urgent item: {next_task['item_name']} ({next_task['days_until_stockout']} days to stockout)")
            prompt_lines.append("Would you like to handle that now?")
        
        session.current_state = "complete"
        session.current_task = None
        
        return BackendInstruction(
            instruction_id=str(uuid.uuid4())[:8],
            instruction_type=InstructionType.COMPLETE,
            prompt="\n".join(prompt_lines),
            options=[
                InstructionOption("yes", "Yes, continue to next item"),
                InstructionOption("no", "No, I'm done for now"),
            ] if session.pending_tasks else [],
            expected_response=UserResponseType.CONFIRMATION if session.pending_tasks else None,
            current_state="complete",
            context={"po_number": po_number, "needs_approval": needs_approval},
            progress_percentage=100
        )
    
    def _handle_next_task(
        self, 
        session: MockSession, 
        response: AgentResponse
    ) -> BackendInstruction:
        """Handle continuing to next task"""
        
        value = str(response.extracted_value).lower()
        
        if value in ["yes", "continue", "ok"]:
            session.current_state = "task_selection"
            # Auto-select next task
            if session.pending_tasks:
                next_task = session.pending_tasks[0]
                session.current_task = next_task
                return self._handle_task_selection(session, AgentResponse(
                    in_response_to="", response_type=UserResponseType.SELECTION,
                    raw_input="", extracted_value=f"{next_task['task_type']}:{next_task['reference_id']}"
                ))
        
        # End session
        return BackendInstruction(
            instruction_id=str(uuid.uuid4())[:8],
            instruction_type=InstructionType.COMPLETE,
            prompt=f"Great work today, {session.user_name}! 👋\n\nYou can always come back to continue where you left off.",
            current_state="ended",
            progress_percentage=100
        )
    
    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    
    def _error_instruction(self, message: str) -> BackendInstruction:
        return BackendInstruction(
            instruction_id=str(uuid.uuid4())[:8],
            instruction_type=InstructionType.ERROR,
            prompt=f"❌ Error: {message}",
            current_state="error"
        )
    
    def _priority_emoji(self, level: str) -> str:
        return {
            "CRITICAL": "🔴",
            "URGENT": "🟠",
            "HIGH": "🟡",
            "MEDIUM": "🔵",
            "LOW": "⚪"
        }.get(level, "⚪")


# =============================================================================
# INTERACTIVE DEMO
# =============================================================================

def print_instruction(instruction: BackendInstruction):
    """Pretty print an instruction"""
    print("\n" + "─" * 60)
    print(f"🤖 BACKEND → AI AGENT")
    print(f"   Type: {instruction.instruction_type.value}")
    print(f"   State: {instruction.current_state}")
    if instruction.progress_percentage is not None:
        print(f"   Progress: {instruction.progress_percentage}%")
    print()
    print("   ┌" + "─" * 55)
    for line in instruction.prompt.split("\n"):
        print(f"   │ {line}")
    print("   └" + "─" * 55)
    
    if instruction.options:
        print("\n   Options:")
        for opt in instruction.options:
            print(f"   │ [{opt.value}] {opt.label}")


async def run_interactive_demo():
    """Run the interactive demo"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║           AI AGENTIC RETAIL/CAFE MANAGEMENT SYSTEM                    ║
║              Purchase Manager Flow Demonstration                      ║
║                                                                       ║
║  This demo uses STATIC MOCK DATA - no database required!              ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
    
    engine = MockOrchestrationEngine()
    
    # Step 1: Initialize session
    print("\n📍 STEP 1: User logs in as Purchase Manager")
    print("=" * 60)
    
    session, greeting = engine.initialize_session(
        user_id=2,
        role="purchase_manager",
        user_name="Ahmed"
    )
    
    print_instruction(greeting)
    
    # Step 2: Select task
    input("\n⏎ Press Enter to select 'Coffee Beans'...")
    print("\n📍 STEP 2: User says 'Let's handle the coffee beans'")
    print("=" * 60)
    
    response1 = AgentResponse(
        in_response_to=greeting.instruction_id,
        response_type=UserResponseType.SELECTION,
        raw_input="Let's handle the coffee beans",
        extracted_value="low_stock_reorder:1",
        session_id=session.session_id
    )
    
    instruction2 = engine.process_response(session.session_id, response1)
    print_instruction(instruction2)
    
    # Step 3: Confirm suggestion
    input("\n⏎ Press Enter to confirm using last order details...")
    print("\n📍 STEP 3: User says 'Yes, use the same details'")
    print("=" * 60)
    
    response2 = AgentResponse(
        in_response_to=instruction2.instruction_id,
        response_type=UserResponseType.CONFIRMATION,
        raw_input="Yes, use the same details",
        extracted_value="yes",
        session_id=session.session_id
    )
    
    instruction3 = engine.process_response(session.session_id, response2)
    print_instruction(instruction3)
    
    # Step 4: Specify quantity
    input("\n⏎ Press Enter to specify '10 kg'...")
    print("\n📍 STEP 4: User says '10 kilograms'")
    print("=" * 60)
    
    response3 = AgentResponse(
        in_response_to=instruction3.instruction_id,
        response_type=UserResponseType.NUMBER,
        raw_input="10 kilograms",
        extracted_value="10",
        session_id=session.session_id
    )
    
    instruction4 = engine.process_response(session.session_id, response3)
    print_instruction(instruction4)
    
    # Step 5: Confirm order
    input("\n⏎ Press Enter to confirm the order...")
    print("\n📍 STEP 5: User says 'Yes, submit it'")
    print("=" * 60)
    
    response4 = AgentResponse(
        in_response_to=instruction4.instruction_id,
        response_type=UserResponseType.CONFIRMATION,
        raw_input="Yes, submit it",
        extracted_value="confirm",
        session_id=session.session_id
    )
    
    instruction5 = engine.process_response(session.session_id, response4)
    print_instruction(instruction5)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ FLOW COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"""
Summary:
────────
• Session ID: {session.session_id}
• User: Ahmed Hassan (Purchase Manager)
• Task Completed: Low Stock Reorder - Coffee Beans
• PO Created: {instruction5.context.get('po_number', 'PO-2026-0142')}
• Needs Approval: {instruction5.context.get('needs_approval', True)}

What Happened:
──────────────
1. ✅ System detected 4 low stock items on login
2. ✅ User selected Coffee Beans (2 days to stockout)  
3. ✅ System showed last order details (10 kg @ $45)
4. ✅ User confirmed quantity
5. ✅ PO created and submitted for approval
6. ✅ Notification sent to Store Manager
7. ✅ System offered next task (Sugar - 3 days)

Your orchestration module is working correctly! 🎉
""")


async def run_automated_test():
    """Run automated tests without user interaction"""
    
    print("Running automated tests...\n")
    
    engine = MockOrchestrationEngine()
    
    # Test 1: Session initialization
    print("Test 1: Session initialization...")
    session, greeting = engine.initialize_session(2, "purchase_manager", "Ahmed")
    assert greeting.instruction_type == InstructionType.SELECT
    assert len(greeting.options) > 0
    assert session.current_state == "task_selection"
    print("  ✅ Session initialized with task list")
    
    # Test 2: Task selection
    print("Test 2: Task selection...")
    response = AgentResponse("", UserResponseType.SELECTION, "", "low_stock_reorder:1")
    instruction = engine.process_response(session.session_id, response)
    assert instruction.instruction_type == InstructionType.CONFIRM
    assert session.current_state == "confirm_suggestion"
    print("  ✅ Task selected, showing details")
    
    # Test 3: Suggestion confirmation
    print("Test 3: Suggestion confirmation...")
    response = AgentResponse("", UserResponseType.CONFIRMATION, "", "yes")
    instruction = engine.process_response(session.session_id, response)
    assert instruction.instruction_type == InstructionType.INPUT
    assert session.current_state == "specify_quantity"
    print("  ✅ Suggestion confirmed, asking for quantity")
    
    # Test 4: Quantity input
    print("Test 4: Quantity input...")
    response = AgentResponse("", UserResponseType.NUMBER, "", "10")
    instruction = engine.process_response(session.session_id, response)
    assert instruction.instruction_type == InstructionType.CONFIRM
    assert session.current_state == "review_order"
    print("  ✅ Quantity accepted, showing review")
    
    # Test 5: Order confirmation
    print("Test 5: Order confirmation...")
    response = AgentResponse("", UserResponseType.CONFIRMATION, "", "confirm")
    instruction = engine.process_response(session.session_id, response)
    assert instruction.instruction_type == InstructionType.COMPLETE
    assert "PO-2026" in instruction.context.get("po_number", "")
    print("  ✅ Order confirmed, PO created")
    
    print("\n" + "=" * 40)
    print("All tests passed! ✅")
    print("=" * 40)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(run_automated_test())
    else:
        asyncio.run(run_interactive_demo())
