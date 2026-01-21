# Implementation Plan - Lingxing Multi-Agent Refactoring

## Goal
Refactor the current monolithic "Lingxing" logic into a flexible, multi-agent system capable of handling specific queries about products (lifecycle, stock, purchasing) and shops (performance, comparison).

## User Review Required
> [!IMPORTANT]
> **External Dependencies**: The reference code (`新品更新流程.py`) relies on `project_run` and `accessory_tool`. I will assume these libraries need to be adapted or mocked within the agent's `app` directory to make the agent self-contained. I will create a `lib` folder to house this ported logic.

> [!NOTE]
> **Architecture Inspiration**: Adopting the **"Manager-Worker" pattern** (similar to *OhMyOpenCode*'s Sisyphus model).
> *   **Manager**: `LingxingManager` (Root) - Plans the workflow, breaks down complex queries, distributes tasks, and aggregates results.
> *   **Workers**: Specialized agents (`ProductWorker`, `ShopWorker`) that focus purely on execution and data retrieval.

## Proposed Changes

### 1. Structure
```
app/
  lingxing_agent/
    manager.py          # [NEW] The "Brain" (Root Agent configuration)
    workers/
        product_worker.py # [NEW] Fetches product lifecycle/status data
        shop_worker.py    # [NEW] Fetches store performance data
    tools/              # Shared tools logic
        product_tools.py
        shop_tools.py
    lib/                # Ported legacy logic
```

### 2. Agent Roles

#### `LingxingManager` (The Orchestrator)
*   **Role**: The "Sisyphus" of the system. It does not run low-level tools itself.
*   **Responsibility**:
    1.  Decompose user requests (e.g., "Why is Shop A doing better than Shop B?").
    2.  **Dispatch** sub-tasks parallelly or sequentially (e.g., "Worker 1: Get Shop A stats", "Worker 2: Get Shop B stats").
    3.  **Synthesize** results into a final report.
*   **Configuration**: Uses `PlanReActPlanner` with specific instructions to *delegate* rather than *do*.

#### `ProductWorker`
*   **Role**: Specialist for MSKU/ASIN data.
*   **Tools**: `check_product_status`, `check_purchase_chain`, `check_stock_flow`.
*   **Output**: Raws structured data (JSON) back to the Manager.

#### `ShopWorker`
*   **Role**: Specialist for Store/Brand data.
*   **Tools**: `get_store_metrics`, `get_cost_structure`.
*   **Output**: Raw structured data (JSON) back to the Manager.

## Verification Plan

### Automated Tests
*   Since we don't have the live ERP API during development, I will create **mock tests** for the new tools.
*   Run `pytest tests/lingxing/test_product_tools.py` (I will create this).

### Manual Verification
*   **Scenario 1: Product Inquiry**
    *   User asks: "Check the status of MSKU '21SZWP...'"
    *   Agent should route to `ProductAgent`, call `get_product_status`, and interpret the result (e.g., "Purchasing not placed", "Stock arrived").
*   **Scenario 2: Shop Comparison**
    *   User asks: "Compare profit for Shop A and Shop B in June."
    *   Agent should route to `ShopAgent`, call `compare_stores`.
