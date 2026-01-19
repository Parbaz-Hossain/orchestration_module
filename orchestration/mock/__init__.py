"""
Mock Module for Orchestration Testing
=====================================

This module provides static mock data and services for testing the orchestration
module without requiring a database connection.

Files:
------
- static_data.py: Mock data store with all business entities
- mock_work_detection.py: Work detection service using mock data  
- mock_po_saga.py: PO creation saga using mock data
- test_pm_flow_static.py: Complete standalone demo (run this!)

Quick Start:
-----------
    # Run the interactive demo
    python test_pm_flow_static.py
    
    # Run automated tests
    python test_pm_flow_static.py --test

Usage in Your Project:
---------------------
    # Option 1: Use the standalone test file
    python test_pm_flow_static.py
    
    # Option 2: Import mock services in your tests
    from orchestration.mock.static_data import get_mock_store
    from orchestration.mock.mock_work_detection import MockWorkDetectionService
    from orchestration.mock.mock_po_saga import MockPOCreationSaga
    
    # Get mock data
    store = get_mock_store()
    low_stock = store.get_low_stock_items(organization_id=1)
    
    # Use mock work detector
    detector = MockWorkDetectionService(store)
    tasks = await detector.get_prioritized_work(user_id=2, role="purchase_manager")
    
    # Execute mock saga
    saga = MockPOCreationSaga(store)
    result = await saga.execute({
        "user_id": 2,
        "organization_id": 1,
        "item_id": 1,
        "quantity": 10,
        "supplier_id": 1,
        "unit_price": 45.00
    })

Directory Structure:
-------------------
    orchestration/
    ├── mock/                      # ← Add these files here
    │   ├── __init__.py           # This file
    │   ├── static_data.py        # Mock data store
    │   ├── mock_work_detection.py # Mock work detector
    │   ├── mock_po_saga.py       # Mock PO saga
    │   └── test_pm_flow_static.py # Standalone demo
    ├── models/
    ├── services/
    ├── workflows/
    └── ...
"""

# Exports
from .static_data import (
    MockDataStore,
    get_mock_store,
    reset_mock_store,
    MockUser,
    MockItem,
    MockSupplier,
    MockPurchaseOrder,
    MockReorderRequest,
    MockApprovalRequest,
)

from .mock_work_detection import (
    MockWorkDetectionService,
    get_purchase_manager_tasks,
)

from .mock_po_saga import (
    MockPOCreationSaga,
    SagaResult,
    SagaStepResult,
)

__all__ = [
    # Data Store
    "MockDataStore",
    "get_mock_store",
    "reset_mock_store",
    # Data Classes
    "MockUser",
    "MockItem", 
    "MockSupplier",
    "MockPurchaseOrder",
    "MockReorderRequest",
    "MockApprovalRequest",
    # Services
    "MockWorkDetectionService",
    "get_purchase_manager_tasks",
    # Saga
    "MockPOCreationSaga",
    "SagaResult",
    "SagaStepResult",
]