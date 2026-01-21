from datetime import datetime, timedelta
from app.lingxing_agent.core.client import LingXingClient

api_client = LingXingClient()

def _process_purchase_date(data, store):
    """Logic to check purchase status for standard products."""
    # Data structure adaptation: client.py might return dict directly or response json
    # _post calls response.json(), so it's a dict.
    # But some methods in reference used 'data' key wrapper, client. _post returns full json.
    
    order_list = data.get('data', {}).get('list', [])
    if data.get('list'): 
        order_list = data.get('list')
        
    print(f"[DEBUG] _process_purchase_date: Found {len(order_list)} orders. Filtering for store: '{store}'")
    
    if not order_list:
        if data.get('data'):
             print(f"[DEBUG] _process_purchase_date: data keys: {data['data'].keys()}")
        return "采购未下单", '缺失', "异常状态"

    earliest_finish_time = None
    earliest_order_time = None
    
    filtered_count = 0
    valid_count = 0

    for order in order_list:
        if int(order.get('quantity_entry', 0)) == 0 and order.get('status_text') != "待到货":
            filtered_count += 1
            continue

        item_list = order.get('item_list', [])
        store_list = [item.get('seller_name') for item in item_list]

        if store and store not in store_list: # Allow empty store check if needed? No, logic requires it.
            print(f"[DEBUG] Filtering out order {order.get('order_number')}, Store: {store}, Actual: {store_list}")
            filtered_count += 1
            continue
            
        valid_count += 1
        finish_time = order.get('finish_time')
        order_time = order.get('order_time')

        if finish_time and finish_time != '-' and (earliest_finish_time is None or finish_time < earliest_finish_time):
            earliest_finish_time = finish_time

        if earliest_order_time is None or (order_time and order_time < earliest_order_time):
            earliest_order_time = order_time

    print(f"[DEBUG] _process_purchase_date: {valid_count} valid orders, {filtered_count} filtered out.")

    if earliest_finish_time:
        return earliest_order_time, earliest_finish_time, "采购已到达"
    elif earliest_order_time:
        return earliest_order_time, '缺失', "采购未到达"
    return '采购未下单', '缺失', "采购未下单"

def _process_purchase_data_processing(data, store):
    """Logic to check purchase status for processing products."""
    process_list = data.get('data', {}).get('list', [])
    # Wait, the reference code did `process_list = data.get('list', [])`
    # But `request_web_processing_purchasedate` in reference returned response, then .json().
    # Let's double check data structure.
    # The reference: data_json = request_web_processing_purchasedate(token, row.SKU).json()
    # Then calling process_purchase_data_processing(data_json...).
    # Inside process_purchase_data_processing: process_list = data.get('list', [])
    # BUT my grep of `request_web_processing_purchasedate` shows it posts to `/api/storage_process/lists`.
    # Usually lingxing API returns {code:0, data: {list: [...]}}.
    # The reference might have stripped 'data' or the API is flat?
    # Let's err on side of caution: try data.get('list') first, if empty/None try data.get('data').get('list').
    
    process_list = data.get('list')
    if process_list is None:
        process_list = data.get('data', {}).get('list', [])
    
    print(f"[DEBUG] _process_purchase_data_processing: Found {len(process_list)} items. Filtering for store: '{store}'")

    if not process_list:
        return "采购未下单", '缺失', "异常状态"

    earliest_finish_time = None
    earliest_create_time = None
    
    filtered_count = 0
    valid_count = 0

    for item in process_list:
        if int(item.get('status', 0)) == 3: # Cancelled
            filtered_count += 1
            continue
            
        item_list = item.get('product_list', [])
        store_list = [idx.get('seller_name') for idx in item_list]

        if store and store not in store_list:
            filtered_count += 1
            continue
        
        valid_count += 1
        finish_time = item.get('finish_time')
        create_time = item.get('create_time')

        if finish_time and finish_time != '-' and (earliest_finish_time is None or finish_time < earliest_finish_time):
            earliest_finish_time = finish_time

        if earliest_create_time is None or (create_time and create_time < earliest_create_time):
            earliest_create_time = create_time
            
    print(f"[DEBUG] _process_purchase_data_processing: {valid_count} valid items, {filtered_count} filtered out.")

    if earliest_finish_time:
        return earliest_create_time, earliest_finish_time, "采购已到达"
    elif earliest_create_time:
        return earliest_create_time, '缺失', "采购未到达"
    return '采购未下单', '缺失', "采购未下单"

def get_initial_outbound(token, msku, shop):
    """
    Check initial shipment info (FBA or Oversea Plan).
    Returns (total_quantity, earliest_shipment_time).
    """
    print(f"[DEBUG] get_initial_outbound: Checking for MSKU: {msku}, Shop: {shop}")
    
    # 1. Try Oversea Plan (request_web_multi_sku_shiptitme equivalent)
    # This seems to be the primary source for "shipment time" in original code
    try:
        plan_response = api_client.request_oversea_plan(msku)
        # response structure: data -> plan_list
        plans = []
        if plan_response.get('data') and plan_response['data'].get('plan_list'):
            plans = plan_response['data']['plan_list']
        elif plan_response.get('plan_list'):
             plans = plan_response['plan_list']
        
        print(f"[DEBUG] get_initial_outbound (Oversea Plan): Found {len(plans)} plans.")
        
        filtered_plans = []
        if plans:
            # Filter by shop/store if needed, but the original code didn't seem to filter strictly by shop in the request loop
            # But we should probably check if it relates to the store
            for plan in plans:
                 # Check 'store_name' or similar if available? 
                 # The response structure from original code inspection didn't show exact store key in the small snippet
                 # But usually these lists have store info. Let's assume valid for now or check fields.
                 filtered_plans.append(plan)

        if filtered_plans:
             # Find earliest plan
             # Time field: 'gmt_create' or 'created_at'? Original code used 'gmt_create' for search but didn't show sort key clearly in snippet.
             # Request used 'sort_field': 'create_time' or 'gmt_create'
             # Let's try 'gmt_create' or 'create_time'
             earliest_plan = min(filtered_plans, key=lambda x: x.get('gmt_create') or x.get('create_time') or '9999-99-99')
             ship_time = earliest_plan.get('gmt_create') or earliest_plan.get('create_time')
             # Quantity? 'plan_quantity'? 'quantity'?
             qty = earliest_plan.get('plan_quantity', 0)
             if ship_time:
                 print(f"[DEBUG] get_initial_outbound (Oversea Plan): Found plan. Time: {ship_time}, Qty: {qty}")
                 return qty, ship_time
    except Exception as e:
        print(f"Error fetching oversea plan: {e}")

    # 2. Fallback to Shipment Plan (request_deliver_page)
    try:
        response_data = api_client.request_deliver_page(msku)
        
        batches = response_data.get('data', {}).get('list', [])
        print(f"[DEBUG] get_initial_outbound (Shipment Plan): Found {len(batches)} batches.")
        
        if not batches:
            return 0, None

        batches = [x for x in batches if x.get('total_quantity_shipped') != 0]

        filtered_data = [
            x for x in batches
            if any(s.get('sname') == shop for s in x.get('relate_list', []))
        ]

        if filtered_data:
            earliest_shipment = min(filtered_data, key=lambda x: datetime.strptime(x['shipment_time'], '%Y-%m-%d %H:%M:%S'))
            earliest_date = datetime.strptime(earliest_shipment['shipment_time'], '%Y-%m-%d %H:%M:%S')
            
            # Simple logic: return total count of this earliest batch
            total_good_num = abs(earliest_shipment.get('total_quantity_shipped', 0))
            print(f"[DEBUG] get_initial_outbound (Shipment Plan): Found match. Time: {earliest_shipment['shipment_time']}, Qty: {total_good_num}")
            return total_good_num, earliest_shipment['shipment_time']
        else:
            print(f"[DEBUG] get_initial_outbound (Shipment Plan): No batches matched shop '{shop}'.")
            
    except Exception as e:
        print(f"Error fetching shipment plan: {e}")

    return 0, None

def check_product_status(msku: str, store_name: str, is_processing: bool = False):
    """
    Check the full status of a product: purchasing, arrival, and initial outbound.
    
    Args:
        msku: The Merchant SKU.
        store_name: The name of the store (e.g., 'Amazon US').
        is_processing: Whether it is a processing product (jiagong).
    """
    sku = msku 
    result = {
        "msku": msku,
        "store": store_name,
        "status": "Unknown",
        "purchase_status": "",
        "purchase_time": "",
        "arrival_time": "",
        "initial_stock_num": 0,
        "initial_stock_time": "",
        "is_borrowed": False
    }

    # 1. Purchase Status
    if is_processing:
        data_json = api_client.request_web_processing_purchasedate(sku)
        purchase_status, finish_time, rank_status = _process_purchase_data_processing(data_json, store_name)
    else:
        # First try standard
        data_json = api_client.request_web_purchasedate(sku)
        
        # Check if list is empty
        has_list = False
        if data_json.get('data') and data_json['data'].get('list'):
             has_list = True
        elif data_json.get('list'): # Some endpoints flat
             has_list = True

        if not has_list:
             # Try processing API just in case
             proc_data = api_client.request_web_processing_purchasedate(sku)
             proc_has_list = bool(proc_data.get('list') or proc_data.get('data', {}).get('list'))
             
             if proc_has_list:
                 # It IS a processing product
                 data_json = proc_data
                 purchase_status, finish_time, rank_status = _process_purchase_data_processing(data_json, store_name)
             else:
                 purchase_status, finish_time, rank_status = _process_purchase_date(data_json, store_name)
        else:
            purchase_status, finish_time, rank_status = _process_purchase_date(data_json, store_name)

    result['purchase_status'] = rank_status
    if purchase_status != "采购未下单":
        result['purchase_time'] = purchase_status
    if finish_time and finish_time != '缺失':
        result['arrival_time'] = finish_time
        
    # Check for Borrowing (Jie-Diao) logic
    if purchase_status == "采购未下单":
        result['status'] = "采购未下单"
        result['is_borrowed'] = True
    elif rank_status == "采购未到达":
        result['status'] = "采购已下单，未到达"
    else:
        result['status'] = "采购已完成"

    # 2. Initial Outbound (Stock)
    stock_num, stock_date = get_initial_outbound(None, msku, store_name)
    result['initial_stock_num'] = stock_num
    result['initial_stock_time'] = stock_date

    # Final logic
    if not stock_num:
         result['status_detail'] = "无首次发货记录"
    else:
         if purchase_status == "采购未下单" or rank_status == "采购未到达":
             result['is_borrowed'] = True
             result['status'] = "借调发货" # Borrowed stock for shipment
         else:
             result['status'] = "正常发货"

    return result


def get_product_performance(msku: str, start_date: str = None, end_date: str = None):
    """
    获取产品的销售表现数据，包括销量、销售额、广告花费等。
    
    Args:
        msku: 产品的 MSKU。
        start_date: 查询开始日期 (YYYY-MM-DD)。如果不提供，默认为本月1号。
        end_date: 查询结束日期 (YYYY-MM-DD)。如果不提供，默认为今天。
    
    Returns:
        包含销量、销售额、广告花费等指标的字典。
    """
    from datetime import datetime as dt
    
    # Default date range: current month
    if not end_date:
        end_date = dt.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = dt.now().strftime("%Y-%m-01")
    
    response = api_client.get_product_performance(start_date, end_date, msku)
    
    # 尝试多种可能的数据路径
    # 依据提供的 JSON 结构: data -> list
    records = []
    if isinstance(response, dict):
        data_block = response.get('data', {})
        if isinstance(data_block, dict):
            records = data_block.get('list', [])
    
    if not records:
        # 返回调试信息以便排查
        return {
            "msku": msku, 
            "error": "未找到该产品的表现数据", 
            "start_date": start_date, 
            "end_date": end_date,
            "debug_response_keys": list(response.keys()) if isinstance(response, dict) else str(type(response)),
            "debug_data_keys": list(response.get('data', {}).keys()) if isinstance(response.get('data'), dict) else None
        }
    
    # Find the specific MSKU record
    product_data = next((r for r in records if r.get('msku') == msku), None)
    # 如果找不到精确匹配，检查 price_list
    if not product_data:
        for record in records:
            price_list = record.get('price_list', [])
            for price_item in price_list:
                if price_item.get('seller_sku') == msku:
                    product_data = record
                    product_data['storeName'] = price_item.get('seller_name', '')
                    break
            if product_data:
                break
    
    if not product_data:
        return {
            "msku": msku,
            "error": f"在 {len(records)} 条记录中未找到 MSKU: {msku}",
            "start_date": start_date,
            "end_date": end_date,
            "available_mskus": [r.get('msku', 'N/A') for r in records[:5]]  # 显示前5个可用的 MSKU
        }
    
    # 使用原始代码中的字段名映射
    result = {
        "msku": product_data.get('msku', msku),
        "asin": product_data.get('asin', product_data.get('asins', [{}])[0].get('asin', '')),
        "store_name": product_data.get('seller_name', product_data.get('storeName', '')),
        "start_date": start_date,
        "end_date": end_date,
        
        # --- 核心销售指标 ---
        "volume": product_data.get('volume', 0), # 销量
        "sales_amount": product_data.get('amount', 0), # 销售额
        "order_count": product_data.get('order_items', 0), # 订单数
        "avg_price": product_data.get('avg_custom_price', 0), # 平均客单价
        
        # --- 利润指标 ---
        "gross_profit": product_data.get('gross_profit', 0), # 毛利额
        "gross_profit_rate": product_data.get('gross_margin', 0), # 毛利率 (gross_margin seems to be rate in 0.xxxx format)
        "roi": product_data.get('roi', 0), # ROI
        
        # --- 广告指标 ---
        "ad_spend": product_data.get('spend', 0), # 广告花费
        "ad_sales": product_data.get('ad_sales_amount', 0), # 广告销售额
        "ad_acos": product_data.get('acos', 0), # ACOS
        "ad_cpc": product_data.get('cpc', 0), # CPC
        "ad_ctr": product_data.get('ctr', 0), # CTR
        "ad_impressions": product_data.get('impressions', 0), # 曝光
        "ad_clicks": product_data.get('clicks', 0), # 点击
        "ad_conversion_rate": product_data.get('ad_cvr', 0), # 广告转化率
        
        # --- 退货指标 ---
        "refund_count": product_data.get('return_goods_count', 0), # 退货数
        "refund_rate": product_data.get('return_goods_rate', 0), # 退货率
        
        # --- 库存指标 ---
        "inventory_sellable": product_data.get('available_inventory', {}).get('afn_fulfillable_quantity', 0), # 可售
        "inventory_reserved": product_data.get('available_inventory', {}).get('reserved_fc_transfers', 0) + product_data.get('available_inventory', {}).get('reserved_fc_processing', 0), # 预留/调拨
        "inventory_inbound": product_data.get('total_inbound', 0), # 入库中
        
        # --- 排名指标 ---
        "big_rank": product_data.get('cate_rank', 0),
        "rank_category_name": product_data.get('rank_category', ''), # 大类名称
        "small_rank": product_data.get('small_cate_rank', [{}])[0].get('rank', 0) if product_data.get('small_cate_rank') else 0,
        
        # --- 环比/同比 (直接从 API 获取，如果有) ---
        "volume_yoy_ratio": product_data.get('volume_yoy_ratio', 0),
        "amount_yoy_ratio": product_data.get('amount_yoy_ratio', 0),
    }
    return result
