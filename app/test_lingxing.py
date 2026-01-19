import sys
import os
import json

# 将当前目录加入路径，确保能导入 app
sys.path.append(os.getcwd())

from app.lingxing_agent.core.auth import get_token
from app.lingxing_agent.core.client import LingXingClient


def run_test():
    print("=" * 50)
    print("🚀 开始领星 Agent 连通性测试")
    print("=" * 50)

    # 1. 测试登录获取 Token
    print("\n[步骤 1] 正在尝试登录领星...")
    try:
        token = get_token()
        if token:
            print(f"✅ 登录成功！")
            print(f"   Token 预览: {token[:20]}...")
        else:
            print("❌ 登录返回为空，请检查账号密码或加密逻辑。")
            return
    except Exception as e:
        print(f"❌ 登录发生异常: {str(e)}")
        import traceback

        traceback.print_exc()
        return

    # 2. 测试 API 请求
    print("\n[步骤 2] 正在测试 API 请求 (利润报表)...")
    try:
        client = LingXingClient(token=token)
        # 测试最近 3 天的数据
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        print(f"   请求范围: {start_date} 至 {end_date}")
        data = client.get_profit_data(start_date, end_date)

        if data and len(data) > 0:
            print(f"✅ API 请求成功！")
            print(f"   获取到 {len(data)} 个店铺的数据摘要。")
            print(f"   第一个店铺名: {data[0].get('storeName', '未知')}")
        else:
            print("⚠️ API 请求成功但返回数据为空，请确认该时间段内是否有业务数据。")

    except Exception as e:
        print(f"❌ API 请求失败")
        print(f"   错误详情: {str(e)}")
        print(
            "\n💡 提示：如果是 403 错误，可能是服务器 IP 被领星封禁或需要海外/国内代理。"
        )

    print("\n" + "=" * 50)
    print("🏁 测试结束")
    print("=" * 50)


if __name__ == "__main__":
    run_test()
