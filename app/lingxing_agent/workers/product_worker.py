from google.genai import types
from google.adk.agents import Agent
from google.adk.models import Gemini

from app.lingxing_agent.tools.product_tools import check_product_status, get_product_performance


product_worker = Agent(
    name="product_worker",
    model=Gemini(
        model="gemini-2.0-flash",
        generate_content_config=types.GenerateContentConfig(temperature=0.0)
    ),
    instruction="""你是一个专门负责查询单个产品（SKU/MSKU）数据的助手。
    你的主要工作是：
    1. 调用 `check_product_status` 查询产品的采购和发货状态。
    2. 调用 `get_product_performance` 查询产品的销售表现（销量、销售额、广告等）。
    
    规则：
    - 你必须使用中文回复。
    - 当查询状态（如"到货了吗"、"发货了吗"），使用 check_product_status。
    - 当查询表现（如"销量如何"、"利润怎样"），使用 get_product_performance。
    - 返回结构化数据，不要添加过多解释。
    """,
    tools=[check_product_status, get_product_performance],
    output_key="product_data",  # 自动保存到 session.state['product_data']
)
