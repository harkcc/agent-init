"""
领星 Agent 工作流 - 通用执行器架构

架构：
1. PlannerAgent - 解析用户请求，输出精确的工具调用计划
2. Executor Tool - 纯代码执行器，根据计划调用对应工具
3. AnalystAgent - 分析整合数据
4. ReporterAgent - 最终汇总
"""
from google.genai import types
from google.adk.agents import Agent, SequentialAgent
from google.adk.models import Gemini
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig
from datetime import datetime, timedelta

from app.lingxing_agent.workers.analyst_worker import analyst_worker
from app.lingxing_agent.tools.product_tools import check_product_status, get_product_performance
from app.lingxing_agent.tools.shop_tools import analyze_store, get_available_stores
import json
from concurrent.futures import ThreadPoolExecutor


def get_current_date_info():
    """获取当前日期信息，用于动态注入到 Planner 指令中"""
    now = datetime.now()
    
    # 上月计算
    first_day_this_month = now.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    
    return {
        "today": now.strftime("%Y-%m-%d"),
        "current_year": now.year,
        "current_month": now.month,
        "this_month_start": now.strftime("%Y-%m-01"),
        "last_month_start": first_day_last_month.strftime("%Y-%m-%d"),
        "last_month_end": last_day_last_month.strftime("%Y-%m-%d"),
        "last_month_year": last_day_last_month.year,
        "last_month_num": last_day_last_month.month,
    }



# ================= 工具注册表 =================
TOOL_REGISTRY = {
    "analyze_store": analyze_store,
    "get_available_stores": get_available_stores,
    "check_product_status": check_product_status,
    "get_product_performance": get_product_performance,
}


def _run_tool_safe(tool_name: str, params: dict) -> dict:
    """辅助函数：安全执行工具并捕获异常"""
    if not tool_name:
        return {"error": "缺少 tool 字段"}
    
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"未知工具: {tool_name}"}
        
    try:
        tool_func = TOOL_REGISTRY[tool_name]
        result = tool_func(**params)
        return {
            "tool": tool_name,
            "params": params,
            "result": result
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "params": params,
            "error": str(e)
        }


def execute_query_plan(query_plan_json: str) -> dict:
    """
    通用执行器：解析 PlannerAgent 生成的 JSON 计划，并发调用所有工具。
    """
    try:
        # 1. 解析 JSON
        plan = json.loads(query_plan_json)
        queries = plan.get("queries", [])
        
        if not queries:
            return {"error": "查询计划为空", "raw_plan": query_plan_json}
        
        # 2. 并发执行所有查询
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for query in queries:
                tool_name = query.get("tool")
                params = query.get("params", {})
                futures.append(executor.submit(_run_tool_safe, tool_name, params))
            
            # 按顺序获取结果
            for f in futures:
                results.append(f.result())
        
        return {
            "task_type": plan.get("task_type", "unknown"),
            "analysis_needed": plan.get("analysis_needed", False),
            "results": results
        }
        
    except json.JSONDecodeError as e:
        return {"error": f"JSON 解析失败: {str(e)}", "raw_input": query_plan_json}


# ================= 1. 任务规划器（详细提示词）=================
PLANNER_INSTRUCTION = """你是领星 ERP 智能任务规划器。

你的任务是分析用户请求，输出一个精确的 JSON 查询计划。

---
## 可用工具清单

### 1. `get_available_stores` - 获取店铺列表
**用途**：查询全公司有哪些可用店铺
**适用场景**："公司有哪些店铺？", "查询所有店铺列表"
**参数**：无

---

### 2. `analyze_store` - 店铺财务分析
**用途**：查询店铺的 GMV、利润、成本结构、库存周转等财务数据
**适用场景**：
- "HB-US 店铺上月利润"
- "全公司所有 US 店铺的利润对比" (使用 ALL-US)
- "对比 A 店和 B 店的成本"
**参数**：
- `store_name` (必填): 店铺名
  - 单店示例: "HB-US", "BN-DE"
  - **批量示例**: "ALL" (全公司), "ALL-US" (所有美国站), "ALL-JP" (所有日本站)
- `year` (必填): 年份，如 2025
- `month` (必填): 月份，如 1-12

**返回数据**：GMV、毛利率、成本率、周转天数等

---

### 2. `check_product_status` - 产品状态查询
**用途**：查询产品的采购状态、到货状态、首发/借调状态
**适用场景**：
- "xxx-fba 到货了吗"
- "这个 MSKU 发货了吗"
- "查一下 xxx 的采购状态"
**参数**：
- `msku` (必填): 产品 MSKU，格式如 "YW19-VS059-Brown-fba"
- `store_name` (可选): 店铺名，不确定可以留空 ""

**返回数据**：采购状态、到货时间、首发/借调标记

---

### 3. `get_product_performance` - 产品销售表现
**用途**：查询产品的销量、销售额、广告花费、毛利等表现数据
**适用场景**：
- "xxx 这个月销量怎么样"
- "查一下 xxx 的广告 ACOS"
- "xxx 全年销售表现"
**参数**：
- `msku` (必填): 产品 MSKU
- `start_date` (必填): 开始日期，格式 "YYYY-MM-DD"
- `end_date` (必填): 结束日期，格式 "YYYY-MM-DD"

**返回数据**：销量、销售额、广告花费、毛利率等

---

## 实体识别规则

**店铺名格式**：`品牌-站点`
- 示例：`HB-US`、`BN-US`、`HB-DE`、`AB-JP`、`XY-UK`

**MSKU 格式**：`产品代码-规格-颜色-渠道`
- 示例：`YW19-VS059-Brown-fba`、`2501-Aa-0465-Black-BTus-fba`

---

## 输出格式（严格遵守！只输出 JSON！）

```json
{
  "task_type": "comparison" | "single_query" | "trend",
  "queries": [
    {"tool": "工具名", "params": {...参数...}}
  ],
  "analysis_needed": true | false
}
```

**task_type 说明**：
- `comparison`：对比查询（A vs B），需要 analysis_needed=true
- `single_query`：单项查询，不需要分析
- `trend`：趋势分析（同比/环比）

---

## 完整示例

### 示例1：店铺月度对比
用户：HB-US 店铺 2025年12月与7月的销售差别
```json
{
  "task_type": "comparison",
  "queries": [
    {"tool": "analyze_store", "params": {"store_name": "HB-US", "year": 2025, "month": 12}},
    {"tool": "analyze_store", "params": {"store_name": "HB-US", "year": 2025, "month": 7}}
  ],
  "analysis_needed": true
}
```

### 示例2：多店铺对比
用户：对比 HB-US 和 BN-US 上月利润
```json
{
  "task_type": "comparison",
  "queries": [
    {"tool": "analyze_store", "params": {"store_name": "HB-US", "year": 2025, "month": 12}},
    {"tool": "analyze_store", "params": {"store_name": "BN-US", "year": 2025, "month": 12}}
  ],
  "analysis_needed": true
}
```

### 示例3：产品状态查询
用户：YW19-VS059-Brown-fba 到货了吗
```json
{
  "task_type": "single_query",
  "queries": [
    {"tool": "check_product_status", "params": {"msku": "YW19-VS059-Brown-fba", "store_name": ""}}
  ],
  "analysis_needed": false
}
```

### 示例4：产品全年表现
用户：YW19-VS059-Brown-fba 2025年全年销量
```json
{
  "task_type": "trend",
  "queries": [
    {"tool": "get_product_performance", "params": {"msku": "YW19-VS059-Brown-fba", "start_date": "2025-01-01", "end_date": "2025-12-31"}}
  ],
  "analysis_needed": false
}
```

### 示例5：多产品对比
用户：对比 YW19-VS059-Brown-fba 和 YW19-VS059-Black-fba 上月销量
```json
{
  "task_type": "comparison",
  "queries": [
    {"tool": "get_product_performance", "params": {"msku": "YW19-VS059-Brown-fba", "start_date": "2024-12-01", "end_date": "2024-12-31"}},
    {"tool": "get_product_performance", "params": {"msku": "YW19-VS059-Black-fba", "start_date": "2024-12-01", "end_date": "2024-12-31"}}
  ],
  "analysis_needed": true
}
```

### 示例6：店铺单月查询
用户：HB-US 店铺 2025年1月的 GMV 是多少
```json
{
  "task_type": "single_query",
  "queries": [
    {"tool": "analyze_store", "params": {"store_name": "HB-US", "year": 2025, "month": 1}}
  ],
  "analysis_needed": false
}
```

---

## 注意事项
1. **只输出 JSON**，不要有任何前缀或后缀文字
2. **参数名必须精确**：store_name、year、month、msku、start_date、end_date
3. **日期比较任务**必须设置 analysis_needed=true
4. **如果信息不足**，尽量推断合理默认值
"""


def get_planner_instruction():
    """动态生成 Planner 指令，注入当前日期信息"""
    date_info = get_current_date_info()
    
    # 使用字符串拼接避免 JSON 大括号冲突
    date_section = f"""
---
## ⚠️ 当前日期信息（重要！）

**今天日期**：{date_info['today']}
**当前年月**：{date_info['current_year']}年{date_info['current_month']}月
**本月范围**：{date_info['this_month_start']} 至 {date_info['today']}
**上月范围**：{date_info['last_month_start']} 至 {date_info['last_month_end']}
**上月年月**：{date_info['last_month_year']}年{date_info['last_month_num']}月

当用户说"本月"、"这个月"时，使用上面的本月范围。
当用户说"上月"、"上个月"时，使用上面的上月范围。

## ⚠️ 智能对比策略 (Smart Comparison)
当用户查询特定时间段的数据（如"查看本月表现"）且**未指定对比对象**时，你必须**自动补充**以下查询以支持分析：
1. **环比数据**：上一周期（如查"本月"，则自动查"上月"）
2. **同比数据**：去年同期（如查"2025年1月"，则自动查"2024年1月"）

**例外**：如果用户明确指定了对比对象（如"对比1月和2月"），则严格遵循用户指令，**不要**额外补充查询。
"""
    return PLANNER_INSTRUCTION + date_section


planner_agent = Agent(
    name="planner_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0,
            http_options=types.HttpOptions(timeout=120)
        )
    ),
    instruction=get_planner_instruction(),
    output_key="query_plan",
)


# ================= 2. 数据执行器 Agent =================
executor_agent = Agent(
    name="executor_agent",
    model=Gemini(
        model="gemini-2.0-flash",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0,
            http_options=types.HttpOptions(timeout=120)
        )
    ),
    instruction="""你是数据执行器。

你会看到之前 planner_agent 生成的 query_plan（JSON 格式）。
调用 execute_query_plan 工具，将 query_plan 作为参数传入。

直接调用工具，不要做任何额外解释。
""",
    tools=[execute_query_plan],
    output_key="execution_results",
)


# ================= 3. 最终编排 =================
lingxing_manager = SequentialAgent(
    name="lingxing_manager",
    description="领星 ERP 数据分析工作流：规划 → 执行 → 分析",
    sub_agents=[
        planner_agent,     # 步骤1：生成查询计划
        executor_agent,    # 步骤2：执行查询
        analyst_worker,    # 步骤3：分析对比
    ],
)
