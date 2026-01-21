from typing import List, Dict, Any
from app.lingxing_agent.core.config import PROJECT_SID
from app.lingxing_agent.tools.metrics import analyze_store as _analyze_store_impl

def get_available_stores() -> List[str]:
    """
    获取当前系统支持的所有店铺名称列表。
    当用户询问"有哪些店铺"、"公司店铺列表"或需对"所有店铺"进行分析时调用此工具。
    """
    return list(PROJECT_SID.keys())

from concurrent.futures import ThreadPoolExecutor, as_completed

def analyze_store(store_name: str, year: int = None, month: int = None) -> Any:
    """
    分析店铺的利润、成本结构和库存周转数据。支持单店或批量分析。
    
    Args:
        store_name: 
            - 单店: "HB-US"
            - 全店: "ALL"
            - 按站点: "ALL-US", "ALL-DE", "ALL-JP" 等
        year: 年份 (如 2025)
        month: 月份 (1-12)
        
    Returns:
        Dict (单店) 或 List[Dict] (多店)
    """
    if str(store_name).upper().startswith("ALL"):
        # Batch Mode
        all_stores = list(PROJECT_SID.keys())
        target_stores = []
        suffix = str(store_name).upper().replace("ALL", "") # e.g. "-US"
        
        for name in all_stores:
            if suffix == "" or name.endswith(suffix):
                target_stores.append(name)
        
        results = []
        # 使用并发加速批量查询
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_store = {
                executor.submit(_analyze_store_impl, name, year, month): name
                for name in target_stores
            }
            
            for future in as_completed(future_to_store):
                name = future_to_store[future]
                try:
                    res = future.result()
                    if res and "error" not in res:
                        results.append(res)
                except Exception as e:
                    print(f"Error fetching {name}: {e}")
                    pass
                    
        return {"summary": f"Analyzed {len(results)} stores matching '{store_name}'", "details": results}

    return _analyze_store_impl(store_name, year, month)
