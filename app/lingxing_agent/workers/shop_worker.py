from google.genai import types
from google.adk.agents import Agent
from google.adk.models import Gemini

from app.lingxing_agent.tools.shop_tools import analyze_store, get_available_stores


shop_worker = Agent(
    name="shop_worker",
    model=Gemini(
        model="gemini-2.0-flash",
        generate_content_config=types.GenerateContentConfig(temperature=0.0)
    ),
    instruction="""你是一个专门负责查询店铺维度数据的助手。
    你的主要工作是：
    1. 调用 `get_available_stores` 获取公司店铺列表（当用户问及有哪些店铺时）。
    2. 调用 `analyze_store` 分析店铺的利润、成本结构和库存周转情况。
    
    规则：
    1. 你必须使用中文回复。
    2. 你可以处理单个店铺的查询，也可以被多次调用以分别获取不同店铺的数据（由 Manager 协调）。
    3. 如果用户需要对比不同店铺或不同月份的数据，你只需负责提取每个单独请求的数据，综合分析留给 Manager。
    4. 返回的数据应该是结构化的事实数据。
    """,
    tools=[analyze_store, get_available_stores],
    output_key="shop_data",  # 自动保存到 session.state['shop_data']
)
