# ruff: noqa
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.planners import PlanReActPlanner
from google.adk.apps.app import App
from google.adk.models import Gemini
from google.adk.tools import google_search
from google.adk.tools import McpToolset
from mcp import StdioServerParameters
from google.genai import types
import sys
import os
import google.auth

from app.lingxing_agent.tools.metrics import analyze_store

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city or query to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# root_agent = Agent(
#     name="root_agent",
#     model=Gemini(
#         model="gemini-3-Flash",
#         retry_options=types.HttpRetryOptions(attempts=3),
#     ),
#     instruction="""You are a helpful AI assistant designed to provide accurate and useful information.
#     You have access to LingXing ERP data to analyze store performance. 
#     You can retrieve cost structure, profit margins, logistics plans, and inventory turnover for specific stores and months.
#     When asked about store performance, use the `analyze_store` tool.""",
#     tools=[get_weather, get_current_time, analyze_store],
# )
# root_agent = Agent(
#     name="root_agent",
#     model=Gemini(
#         model="gemini-2.5-flash", # 建议使用 Pro 模型处理复杂逻辑
#         retry_options=types.HttpRetryOptions(attempts=3),
#     ),
#     # 👇 这里就是修改 Instruction 的地方
#     instruction="""你是一个专业的领星 ERP 数据分析助手。
    
#     ## 职责：
#     1. 当用户要求分析店铺表现、成本结构或利润时，使用 `analyze_store` 工具。
#     2. 在调用 `analyze_store` 之前，你必须确保已经获得了：店名 (store_name)、年份 (year)、月份 (month)。
    
#     ## 约束：
#     - 如果用户信息缺失（如没说月份），请礼貌地询问：“请问您想查看哪个月份的数据？”。
#     - 拿到数据后，请结合数据给出 2-3 条改进建议。
#     """,
#     tools=[get_weather, get_current_time, analyze_store],
# )

lingxing_agent = Agent(
    name="lingxing_expert",
    model=Gemini(
        model="gemini-2.0-flash",
        generate_content_config=types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(category=c, threshold="BLOCK_NONE")
                for c in [
                    "HATE_SPEECH",
                    "DANGEROUS_CONTENT",
                    "HARASSMENT",
                    "SEXUALLY_EXPLICIT",
                ]
            ]
        ),
    ),
    planner=PlanReActPlanner(),
    instruction="""你是一个领星 ERP 数据分析专家。
    **注意：你必须全程使用中文进行回复。**
    你的思考过程、计划（Planning）和最终答案都必须使用简体中文。
    你负责查询店铺利润、成本结构和库存周转。
    请确保在调用工具前核实店名、年、月。
    分析完成后，请给出专业的财务建议。""",
    output_key="lingxing_report", # 结果存在这里
    tools=[analyze_store], # 领星专用的工具放在这里
)

# 2. 定义独立的搜索 Agent
search_agent = Agent(
    name="search_agent",
    model=Gemini(
        model="gemini-2.0-flash",
        generate_content_config=types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(category=c, threshold="BLOCK_NONE")
                for c in [
                    "HATE_SPEECH",
                    "DANGEROUS_CONTENT",
                    "HARASSMENT",
                    "SEXUALLY_EXPLICIT",
                ]
            ]
        ),
    ),
    tools=[google_search],
    instruction="""你是一个搜索专家。当主控 Agent 委派任务给你时，请使用 google_search 工具查找互联网上的信息。
    **注意：你必须全程使用中文。** 即使搜索到的内容是英文，你也必须将其总结并以中文回答。""",
)

# 3. 定义 MCP Toolset 和 Database Agent
# 获取当前文件所在目录: app/
current_dir = os.path.dirname(os.path.abspath(__file__))
# 拼接 mcp_server/main.py 的路径
mcp_script_path = os.path.join(current_dir, "mcp_server", "main.py")

# 定义连接参数
connection_params = StdioServerParameters(
    command=sys.executable,
    args=[mcp_script_path],
    env={**os.environ, "DEPLOY_ENV": "development"}
)

# 初始化 Toolset
mongo_mcp_toolset = McpToolset(connection_params=connection_params)

database_agent = Agent(
    name="database_agent",
    model=Gemini(
        model="gemini-2.0-flash",
        generate_content_config=types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(category=c, threshold="BLOCK_NONE")
                for c in [
                    "HATE_SPEECH", 
                    "DANGEROUS_CONTENT", 
                    "HARASSMENT", 
                    "SEXUALLY_EXPLICIT"
                ]
            ]
        ),
    ),
    tools=[mongo_mcp_toolset],
    instruction="""你是一个数据库专家，可以通过 MCP 工具集直接访问 MongoDB 数据库。
    你可以列出集合 (list_collections)、查询数据 (query_collection) 和查看统计信息 (get_collection_stats)。
    **新增能力**：你可以直接通过 MSKU 或 SKU 查询产品信息 (find_product_by_msku, find_product_by_sku)。
    
    当用户提供 MSKU 或 SKU 时，优先使用专用的查找工具。
    请根据用户的需求，灵活使用这些工具来获取数据回答问题。
    **注意：你必须全程使用中文回答。**
    """,
)

# 3. 定义【Root Agent】（主控）
root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.0-flash",
        generate_content_config=types.GenerateContentConfig(
            safety_settings=[
                types.SafetySetting(category=c, threshold="BLOCK_NONE")
                for c in [
                    "HATE_SPEECH",
                    "DANGEROUS_CONTENT",
                    "HARASSMENT",
                    "SEXUALLY_EXPLICIT",
                ]
            ]
        ),
    ),
    planner=PlanReActPlanner(),
    instruction="""你是一个全能助手。
    **核心规则：你必须全程使用中文进行交流。** 你的思考逻辑、步骤计划和最终回复都必须是简体中文。
    在执行任务或委派任务之前，请简要说明你的计划，让用户了解你的思考过程。
    
    1. 如果用户的问题涉及领星 ERP、店铺利润、成本分析、财务数据或库存周转，请委派给 'lingxing_expert'。
    2. 如果用户想了解实时新闻、查找互联网信息或进行背景调研，请委派给 'search_agent'。
    3. 如果用户查询具体的产品基础信息，特别是提供了 MSKU（如 '21SZWP-01NS-10color-FBA-JPE'）或 ASIN（如 'B08RRVYJLJ'）格式的标识符时，请直接委派给 'database_agent' 进行精确查询。
    4. 如果用户问数据库底层数据、集合列表或具体的 MongoDB 查询，请委派给 'database_agent'。
    5. 如果用户问天气，使用 get_weather。
    6. 如果用户问时间，使用 get_current_time。
    7. 其他日常闲聊，由你直接回答。
    **注意：你必须全程使用中文回答。** """,
    
    tools=[get_weather, get_current_time], # 移除了 google_search
    sub_agents=[lingxing_agent, search_agent, database_agent], # 挂载了 search_agent 和 database_agent
)


app = App(root_agent=root_agent, name="app")
