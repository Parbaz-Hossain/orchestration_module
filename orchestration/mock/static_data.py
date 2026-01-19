"""
Static Mock Data for Orchestration Module Testing
This file provides all the mock data needed to test the Purchase Manager flow
without requiring a real database connection.

Usage:
    from orchestration.mock.static_data import MockDataStore
    
    store = MockDataStore()
    low_stock_items = store.get_low_stock_items(organization_id=1)
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# =============================================================================
# DATA CLASSES (Simulating ORM Models)
# =============================================================================

@dataclass
class MockOrganization:
    id: int
    name: str
    code: str
    settings: Dict = field(default_factory=dict)


@dataclass
class MockRole:
    id: int
    name: str
    code: str
    permissions: List[str] = field(default_factory=list)


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
    organization_id: int
    code: str
    name: str
    unit_symbol: str
    current_stock: Decimal
    reorder_level: Decimal
    reorder_quantity: Decimal
    avg_daily_usage: Decimal
    cost_price: Decimal
    category_name: str = ""
    storage_location: str = ""
    
    @property
    def days_until_stockout(self) -> int:
        if self.avg_daily_usage <= 0:
            return 999
        return max(0, int(float(self.current_stock) / float(self.avg_daily_usage)))
    
    @property
    def is_below_reorder_level(self) -> bool:
        return self.current_stock <= self.reorder_level


@dataclass
class MockSupplier:
    id: int
    organization_id: int
    code: str
    name: str
    contact_person: str
    email: str
    phone: str
    lead_time_days: int = 3
    payment_terms: str = "Net 30"


@dataclass
class MockItemSupplier:
    item_id: int
    supplier_id: int
    unit_price: Decimal
    is_preferred: bool = False
    last_order_date: Optional[datetime] = None
    last_order_qty: Optional[Decimal] = None
    last_order_price: Optional[Decimal] = None


@dataclass
class MockPurchaseOrder:
    id: int
    organization_id: int
    supplier_id: int
    po_number: str
    status: str
    total_amount: Decimal
    created_at: datetime
    created_by: int
    supplier_name: str = ""
    items_count: int = 0


@dataclass
class MockReorderRequest:
    id: int
    organization_id: int
    item_id: int
    status: str
    current_stock: Decimal
    reorder_level: Decimal
    suggested_quantity: Decimal
    days_until_stockout: int
    created_at: datetime


@dataclass
class MockApprovalRequest:
    id: int
    organization_id: int
    entity_type: str
    entity_id: int
    status: str
    amount: Decimal
    requester_id: int
    approver_id: int
    created_at: datetime


@dataclass
class MockSupplierPayment:
    id: int
    organization_id: int
    supplier_id: int
    supplier_name: str
    invoice_number: str
    amount: Decimal
    due_date: datetime
    status: str
    created_at: datetime


# =============================================================================
# MOCK DATA STORE
# =============================================================================

class MockDataStore:
    """
    Centralized store for all mock data.
    Simulates database queries for testing orchestration flows.
    """
    
    def __init__(self):
        self._init_organizations()
        self._init_roles()
        self._init_users()
        self._init_suppliers()
        self._init_items()
        self._init_item_suppliers()
        self._init_purchase_orders()
        self._init_reorder_requests()
        self._init_approval_requests()
        self._init_supplier_payments()
        
        # Counter for generating new IDs
        self._po_counter = 142
    
    # -------------------------------------------------------------------------
    # Initialization Methods
    # -------------------------------------------------------------------------
    
    def _init_organizations(self):
        self.organizations = {
            1: MockOrganization(
                id=1,
                name="Demo Cafe & Retail",
                code="DEMO-001",
                settings={
                    "currency": "USD",
                    "timezone": "America/New_York",
                    "po_approval_threshold": 100.00,
                    "low_stock_alert_days": 7
                }
            )
        }
    
    def _init_roles(self):
        self.roles = {
            1: MockRole(id=1, name="Store Manager", code="store_manager", permissions=["all"]),
            2: MockRole(id=2, name="Purchase Manager", code="purchase_manager", permissions=["purchase_orders", "suppliers", "reorder"]),
            3: MockRole(id=3, name="Inventory Manager", code="inventory_manager", permissions=["inventory", "stock_count"]),
            4: MockRole(id=4, name="HR Manager", code="hr_manager", permissions=["leave_requests", "attendance"]),
            5: MockRole(id=5, name="Supervisor", code="supervisor", permissions=["view_inventory"]),
        }
    
    def _init_users(self):
        self.users = {
            1: MockUser(id=1, organization_id=1, role_id=1, first_name="Sarah", last_name="Johnson", 
                       email="sarah.johnson@democafe.com", role_code="store_manager"),
            2: MockUser(id=2, organization_id=1, role_id=2, first_name="Ahmed", last_name="Hassan", 
                       email="ahmed.hassan@democafe.com", role_code="purchase_manager"),
            3: MockUser(id=3, organization_id=1, role_id=3, first_name="Maria", last_name="Garcia", 
                       email="maria.garcia@democafe.com", role_code="inventory_manager"),
            4: MockUser(id=4, organization_id=1, role_id=4, first_name="John", last_name="Smith", 
                       email="john.smith@democafe.com", role_code="hr_manager"),
            5: MockUser(id=5, organization_id=1, role_id=5, first_name="Lisa", last_name="Chen", 
                       email="lisa.chen@democafe.com", role_code="supervisor"),
        }
    
    def _init_suppliers(self):
        self.suppliers = {
            1: MockSupplier(id=1, organization_id=1, code="SUP001", name="ACME Coffee Corp",
                           contact_person="Robert Brown", email="orders@acmecoffee.com", 
                           phone="+1-555-1001", lead_time_days=3),
            2: MockSupplier(id=2, organization_id=1, code="SUP002", name="Fresh Dairy Supplies",
                           contact_person="Emily White", email="sales@freshdairy.com",
                           phone="+1-555-1002", lead_time_days=1),
            3: MockSupplier(id=3, organization_id=1, code="SUP003", name="Bakery Wholesale Inc",
                           contact_person="Michael Davis", email="orders@bakerywholesale.com",
                           phone="+1-555-1003", lead_time_days=2),
            4: MockSupplier(id=4, organization_id=1, code="SUP004", name="PackRight Solutions",
                           contact_person="Susan Miller", email="sales@packright.com",
                           phone="+1-555-1004", lead_time_days=5),
        }
    
    def _init_items(self):
        self.items = {
            # CRITICAL: Coffee Beans - 2 days to stockout
            1: MockItem(id=1, organization_id=1, code="ITEM001", name="Coffee Beans (Premium Arabica)",
                       unit_symbol="kg", current_stock=Decimal("0.5"), reorder_level=Decimal("5"),
                       reorder_quantity=Decimal("10"), avg_daily_usage=Decimal("0.25"),
                       cost_price=Decimal("45.00"), category_name="Coffee & Tea", storage_location="Dry Storage A1"),
            
            # CRITICAL: Sugar - 3 days to stockout
            2: MockItem(id=2, organization_id=1, code="ITEM002", name="White Sugar",
                       unit_symbol="kg", current_stock=Decimal("1.5"), reorder_level=Decimal("10"),
                       reorder_quantity=Decimal("25"), avg_daily_usage=Decimal("0.5"),
                       cost_price=Decimal("2.50"), category_name="Bakery Supplies", storage_location="Dry Storage A2"),
            
            # URGENT: Milk - 5 days to stockout
            3: MockItem(id=3, organization_id=1, code="ITEM003", name="Fresh Whole Milk",
                       unit_symbol="L", current_stock=Decimal("20"), reorder_level=Decimal("30"),
                       reorder_quantity=Decimal("50"), avg_daily_usage=Decimal("4"),
                       cost_price=Decimal("3.50"), category_name="Dairy", storage_location="Refrigerator R1"),
            
            # HIGH: Takeaway Cups - 7 days to stockout
            4: MockItem(id=4, organization_id=1, code="ITEM004", name="Takeaway Cups (12oz)",
                       unit_symbol="pc", current_stock=Decimal("150"), reorder_level=Decimal("200"),
                       reorder_quantity=Decimal("500"), avg_daily_usage=Decimal("20"),
                       cost_price=Decimal("0.15"), category_name="Packaging", storage_location="Storage B1"),
            
            # OK: Napkins - above reorder level
            5: MockItem(id=5, organization_id=1, code="ITEM005", name="Paper Napkins",
                       unit_symbol="pack", current_stock=Decimal("25"), reorder_level=Decimal("20"),
                       reorder_quantity=Decimal("50"), avg_daily_usage=Decimal("2"),
                       cost_price=Decimal("5.00"), category_name="Packaging", storage_location="Storage B2"),
            
            # OK: Flour - above reorder level
            6: MockItem(id=6, organization_id=1, code="ITEM006", name="All-Purpose Flour",
                       unit_symbol="kg", current_stock=Decimal("15"), reorder_level=Decimal("10"),
                       reorder_quantity=Decimal("25"), avg_daily_usage=Decimal("1"),
                       cost_price=Decimal("1.80"), category_name="Bakery Supplies", storage_location="Dry Storage A3"),
        }
    
    def _init_item_suppliers(self):
        self.item_suppliers = [
            # Coffee Beans -> ACME Coffee (preferred)
            MockItemSupplier(item_id=1, supplier_id=1, unit_price=Decimal("45.00"), is_preferred=True,
                           last_order_date=datetime.now() - timedelta(days=12),
                           last_order_qty=Decimal("10"), last_order_price=Decimal("45.00")),
            
            # Sugar -> Bakery Wholesale (preferred)
            MockItemSupplier(item_id=2, supplier_id=3, unit_price=Decimal("2.50"), is_preferred=True,
                           last_order_date=datetime.now() - timedelta(days=20),
                           last_order_qty=Decimal("25"), last_order_price=Decimal("2.40")),
            
            # Milk -> Fresh Dairy (preferred)
            MockItemSupplier(item_id=3, supplier_id=2, unit_price=Decimal("3.50"), is_preferred=True,
                           last_order_date=datetime.now() - timedelta(days=3),
                           last_order_qty=Decimal("50"), last_order_price=Decimal("3.50")),
            
            # Cups -> PackRight (preferred)
            MockItemSupplier(item_id=4, supplier_id=4, unit_price=Decimal("0.15"), is_preferred=True,
                           last_order_date=datetime.now() - timedelta(days=30),
                           last_order_qty=Decimal("500"), last_order_price=Decimal("0.14")),
            
            # Flour -> Bakery Wholesale
            MockItemSupplier(item_id=6, supplier_id=3, unit_price=Decimal("1.80"), is_preferred=True),
        ]
    
    def _init_purchase_orders(self):
        self.purchase_orders = {
            # Historical completed PO
            1: MockPurchaseOrder(id=1, organization_id=1, supplier_id=1, po_number="PO-2026-0100",
                                status="received", total_amount=Decimal("450.00"),
                                created_at=datetime.now() - timedelta(days=30), created_by=2,
                                supplier_name="ACME Coffee Corp", items_count=1),
            
            # Pending approval PO
            2: MockPurchaseOrder(id=2, organization_id=1, supplier_id=3, po_number="PO-2026-0141",
                                status="pending_approval", total_amount=Decimal("250.00"),
                                created_at=datetime.now() - timedelta(days=5), created_by=2,
                                supplier_name="Bakery Wholesale Inc", items_count=2),
        }
    
    def _init_reorder_requests(self):
        now = datetime.now()
        self.reorder_requests = {
            1: MockReorderRequest(id=1, organization_id=1, item_id=1, status="pending",
                                 current_stock=Decimal("0.5"), reorder_level=Decimal("5"),
                                 suggested_quantity=Decimal("10"), days_until_stockout=2,
                                 created_at=now - timedelta(hours=2)),
            2: MockReorderRequest(id=2, organization_id=1, item_id=2, status="pending",
                                 current_stock=Decimal("1.5"), reorder_level=Decimal("10"),
                                 suggested_quantity=Decimal("25"), days_until_stockout=3,
                                 created_at=now - timedelta(hours=3)),
            3: MockReorderRequest(id=3, organization_id=1, item_id=3, status="pending",
                                 current_stock=Decimal("20"), reorder_level=Decimal("30"),
                                 suggested_quantity=Decimal("50"), days_until_stockout=5,
                                 created_at=now - timedelta(hours=4)),
            4: MockReorderRequest(id=4, organization_id=1, item_id=4, status="pending",
                                 current_stock=Decimal("150"), reorder_level=Decimal("200"),
                                 suggested_quantity=Decimal("500"), days_until_stockout=7,
                                 created_at=now - timedelta(hours=5)),
        }
    
    def _init_approval_requests(self):
        self.approval_requests = {
            1: MockApprovalRequest(id=1, organization_id=1, entity_type="purchase_order",
                                  entity_id=2, status="pending", amount=Decimal("250.00"),
                                  requester_id=2, approver_id=1,
                                  created_at=datetime.now() - timedelta(days=5)),
        }
    
    def _init_supplier_payments(self):
        self.supplier_payments = {
            1: MockSupplierPayment(id=1, organization_id=1, supplier_id=1, 
                                  supplier_name="ACME Coffee Corp",
                                  invoice_number="INV-ACME-2026-0050",
                                  amount=Decimal("450.00"),
                                  due_date=datetime.now() + timedelta(days=5),
                                  status="pending",
                                  created_at=datetime.now() - timedelta(days=25)),
            2: MockSupplierPayment(id=2, organization_id=1, supplier_id=2,
                                  supplier_name="Fresh Dairy Supplies",
                                  invoice_number="INV-FD-2026-0033",
                                  amount=Decimal("175.00"),
                                  due_date=datetime.now() + timedelta(days=5),
                                  status="pending",
                                  created_at=datetime.now() - timedelta(days=10)),
        }
    
    # -------------------------------------------------------------------------
    # Query Methods (Simulating Database Queries)
    # -------------------------------------------------------------------------
    
    def get_user(self, user_id: int) -> Optional[MockUser]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_organization(self, user_id: int) -> Optional[int]:
        """Get user's organization ID"""
        user = self.users.get(user_id)
        return user.organization_id if user else None
    
    def get_organization(self, org_id: int) -> Optional[MockOrganization]:
        """Get organization by ID"""
        return self.organizations.get(org_id)
    
    def get_low_stock_items(self, organization_id: int) -> List[Dict[str, Any]]:
        """Get items below reorder level, sorted by urgency"""
        low_stock = []
        for item in self.items.values():
            if item.organization_id == organization_id and item.is_below_reorder_level:
                low_stock.append({
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "unit_symbol": item.unit_symbol,
                    "current_stock": item.current_stock,
                    "reorder_level": item.reorder_level,
                    "reorder_quantity": item.reorder_quantity,
                    "avg_daily_usage": item.avg_daily_usage,
                    "cost_price": item.cost_price,
                    "days_until_stockout": item.days_until_stockout,
                    "category_name": item.category_name,
                    "storage_location": item.storage_location,
                })
        
        # Sort by days_until_stockout (most urgent first)
        return sorted(low_stock, key=lambda x: x["days_until_stockout"])
    
    def get_preferred_supplier(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get preferred supplier for an item"""
        for item_sup in self.item_suppliers:
            if item_sup.item_id == item_id and item_sup.is_preferred:
                supplier = self.suppliers.get(item_sup.supplier_id)
                if supplier:
                    return {
                        "supplier_id": supplier.id,
                        "supplier_name": supplier.name,
                        "unit_price": item_sup.unit_price,
                        "lead_time_days": supplier.lead_time_days,
                        "last_order_date": item_sup.last_order_date,
                        "last_order_qty": item_sup.last_order_qty,
                        "last_order_price": item_sup.last_order_price,
                    }
        return None
    
    def get_last_order_info(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Get last order information for an item"""
        for item_sup in self.item_suppliers:
            if item_sup.item_id == item_id and item_sup.last_order_date:
                supplier = self.suppliers.get(item_sup.supplier_id)
                return {
                    "quantity": str(item_sup.last_order_qty),
                    "unit_price": str(item_sup.last_order_price or item_sup.unit_price),
                    "order_date": item_sup.last_order_date.strftime("%b %d, %Y"),
                    "supplier_name": supplier.name if supplier else "Unknown",
                }
        return None
    
    def get_pending_po_approvals(self, organization_id: int) -> List[Dict[str, Any]]:
        """Get purchase orders pending approval"""
        pending = []
        for po in self.purchase_orders.values():
            if po.organization_id == organization_id and po.status == "pending_approval":
                days_pending = (datetime.now() - po.created_at).days
                pending.append({
                    "id": po.id,
                    "po_number": po.po_number,
                    "supplier_name": po.supplier_name,
                    "total_amount": po.total_amount,
                    "created_at": po.created_at,
                    "days_pending": days_pending,
                    "items_count": po.items_count,
                    "requested_by_name": self.users.get(po.created_by, MockUser(0,0,0,"Unknown","","")).first_name,
                })
        return pending
    
    def get_payment_dues(self, organization_id: int, days_ahead: int = 14) -> List[Dict[str, Any]]:
        """Get upcoming/overdue payments"""
        cutoff = datetime.now() + timedelta(days=days_ahead)
        dues = []
        for payment in self.supplier_payments.values():
            if (payment.organization_id == organization_id and 
                payment.status in ["pending", "overdue"] and
                payment.due_date <= cutoff):
                dues.append({
                    "id": payment.id,
                    "supplier_name": payment.supplier_name,
                    "invoice_number": payment.invoice_number,
                    "amount": payment.amount,
                    "due_date": payment.due_date,
                    "status": payment.status,
                    "created_at": payment.created_at,
                })
        return sorted(dues, key=lambda x: x["due_date"])
    
    def get_pending_approvals_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get pending approvals assigned to a user"""
        pending = []
        for approval in self.approval_requests.values():
            if approval.approver_id == user_id and approval.status == "pending":
                days_pending = (datetime.now() - approval.created_at).days
                requester = self.users.get(approval.requester_id)
                pending.append({
                    "id": approval.id,
                    "entity_type": approval.entity_type,
                    "entity_id": approval.entity_id,
                    "amount": approval.amount,
                    "days_pending": days_pending,
                    "requester_name": requester.first_name if requester else "Unknown",
                    "title": f"{approval.entity_type.replace('_', ' ').title()} #{approval.entity_id}",
                })
        return pending
    
    def get_store_manager(self, organization_id: int) -> Optional[MockUser]:
        """Get store manager for approval routing"""
        for user in self.users.values():
            if user.organization_id == organization_id and user.role_code == "store_manager":
                return user
        return None
    
    def get_item(self, item_id: int) -> Optional[MockItem]:
        """Get item by ID"""
        return self.items.get(item_id)
    
    def get_supplier(self, supplier_id: int) -> Optional[MockSupplier]:
        """Get supplier by ID"""
        return self.suppliers.get(supplier_id)
    
    # -------------------------------------------------------------------------
    # Mutation Methods (Simulating Database Updates)
    # -------------------------------------------------------------------------
    
    def generate_po_number(self) -> str:
        """Generate new PO number"""
        year = datetime.now().year
        self._po_counter += 1
        return f"PO-{year}-{self._po_counter:04d}"
    
    def create_purchase_order(self, data: Dict[str, Any]) -> MockPurchaseOrder:
        """Create a new purchase order"""
        po_id = max(self.purchase_orders.keys()) + 1
        supplier = self.suppliers.get(data["supplier_id"])
        
        po = MockPurchaseOrder(
            id=po_id,
            organization_id=data["organization_id"],
            supplier_id=data["supplier_id"],
            po_number=data["po_number"],
            status=data.get("status", "draft"),
            total_amount=Decimal(str(data["total_amount"])),
            created_at=datetime.now(),
            created_by=data["created_by"],
            supplier_name=supplier.name if supplier else "Unknown",
            items_count=data.get("items_count", 1),
        )
        self.purchase_orders[po_id] = po
        return po
    
    def update_reorder_request(self, reorder_id: int, updates: Dict[str, Any]) -> None:
        """Update a reorder request"""
        if reorder_id in self.reorder_requests:
            rr = self.reorder_requests[reorder_id]
            for key, value in updates.items():
                if hasattr(rr, key):
                    setattr(rr, key, value)
    
    def create_approval_request(self, data: Dict[str, Any]) -> MockApprovalRequest:
        """Create a new approval request"""
        approval_id = max(self.approval_requests.keys()) + 1
        
        approval = MockApprovalRequest(
            id=approval_id,
            organization_id=data["organization_id"],
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            status="pending",
            amount=Decimal(str(data["amount"])),
            requester_id=data["requester_id"],
            approver_id=data["approver_id"],
            created_at=datetime.now(),
        )
        self.approval_requests[approval_id] = approval
        return approval


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Global mock data store instance
_mock_store: Optional[MockDataStore] = None

def get_mock_store() -> MockDataStore:
    """Get or create the singleton mock data store"""
    global _mock_store
    if _mock_store is None:
        _mock_store = MockDataStore()
    return _mock_store

def reset_mock_store() -> MockDataStore:
    """Reset the mock data store (useful for testing)"""
    global _mock_store
    _mock_store = MockDataStore()
    return _mock_store