import asyncio
import os
from app.agent import root_agent
from google.adk.runners import Runner

async def main():
    print("--- 正在直接测试 root_agent (跳过 Web UI) ---")
    runner = Runner(agent=root_agent)
    
    # 模拟一个领星查询
    query = "帮我分析一下 BT-US 店铺在 2024 年 12 月的表现。"
    print(f"用户提问: {query}")
    
    try:
        async for event in runner.run_async(query):
            # 打印流式输出的类型，方便我们看它在哪一步卡住了
            if hasattr(event, 'content') and event.content:
                print(f"[回复]: {event.content}")
            if hasattr(event, 'actions') and event.actions:
                for action in event.actions:
                    print(f"[动作]: 调用了 {action.tool_name}")
    except Exception as e:
        print(f"\n❌ 捕获到异常!!")
        print(f"报错详情: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
