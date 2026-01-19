from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict
from app.lingxing_agent.core.client import LingXingClient
from app.lingxing_agent.core.config import get_store_id, PROJECT_SID, PROJECT_WID


class LingXingMetricsService:
    def __init__(self, client: LingXingClient):
        self.client = client

    def _get_month_range(self, year: int, month: int):
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        # Calculate last day of month by subtracting 1 day from first day of next month
        next_month_first = datetime(next_year, next_month, 1)
        end_date = (next_month_first - timedelta(days=1)).strftime("%Y-%m-%d")
        return start_date, end_date

    def get_store_cost_structure(
        self, store_name: str, year: int, month: int
    ) -> Dict[str, Any]:
        """获取指定店铺、月份的成本结构分析"""
        start_date, end_date = self._get_month_range(year, month)

        # 1. 统一店名匹配 (Handle fuzzy matching once at the start)
        canonical_store_name = None
        for name in PROJECT_SID:
            if store_name == name:
                canonical_store_name = name
                break
        if not canonical_store_name:
            for name in PROJECT_SID:
                if store_name.upper() in name.upper():
                    canonical_store_name = name
                    break
        
        if not canonical_store_name:
            return {"error": f"Store {store_name} not found in configuration"}

        sid = PROJECT_SID[canonical_store_name]
        
        # 1. 获取利润报表数据 (Aggregation is done in client for all stores, we filter here)
        # Note: Optimization possible by filtering in client if API supported it, but API takes list of SIDs.
        # We can pass specific SID to client if we want.
        # Client method fetches for ALL stores currently because I didn't expose SID filter in `get_profit_data` properly?
        # Let's check client.py. I passed `sids=[]` in get_profit_data.
        # Ideally I should allow passing SID to get_profit_data to reduce data load.
        # But for now, let's assume we fetch all and filter, or I update client.py later.
        # Actually, let's update client.py to accept sids later if needed.
        # For now, fetching all is fine for the scale (20 stores).

        profit_data_list = self.client.get_profit_data(start_date, end_date)
        store_data = next(
            (item for item in profit_data_list if item.get("storeName") == canonical_store_name),
            None,
        )

        if not store_data:
            return {"error": f"No profit data found for {canonical_store_name} in {year}-{month}"}

        # Calculate Metrics
        total_amount_origin = (
            store_data.get("totalFbaAndFbmAmount", 0)
            + store_data.get("shippingCredits", 0)
            + store_data.get("promotionalRebates", 0)
            + store_data.get("fbaInventoryCredit", 0)
            + store_data.get("cashOnDelivery", 0)
            + store_data.get("otherInAmount", 0)
            + store_data.get("totalSalesRefunds", 0)
            + store_data.get("totalSalesTax", 0)
            + store_data.get("salesTaxRefund", 0)
            + store_data.get("salesTaxWithheld", 0)
            + store_data.get("refundTaxWithheld", 0)
        )

        metrics = {
            "GMV": total_amount_origin,
            "year": year,
            "month": month,
            "store_name": store_name,
        }

        if total_amount_origin == 0:
            metrics.update(
                {
                    "gross_profit_rate": 0,
                    "head_trip_cost_rate": 0,
                    "storage_fee_rate": 0,
                    "cogs_rate": 0,
                    "tail_trip_rate": 0,
                    "marketing_rate": 0,
                    "commission_rate": 0,
                }
            )
        else:
            metrics["gross_profit_rate"] = (
                store_data.get("grossProfit", 0) / total_amount_origin
            )
            metrics["head_trip_cost_rate"] = (
                store_data.get("cgTransportCostsTotal", 0) / total_amount_origin
            )
            metrics["storage_fee_rate"] = (
                store_data.get("totalStorageFee", 0) / total_amount_origin
            )
            metrics["cogs_rate"] = (
                store_data.get("cgPriceTotal", 0) / total_amount_origin
            )
            metrics["tail_trip_rate"] = (
                store_data.get("fbaDeliveryFee", 0)
                + store_data.get("fbaTransactionFeeRefunds", 0)
            ) / total_amount_origin
            metrics["marketing_rate"] = (
                sum(
                    float(store_data.get(key, 0))
                    for key in ["totalAdsCost", "promotionFee"]
                )
                / total_amount_origin
            )
            metrics["commission_rate"] = (
                abs(store_data.get("platformFee", 0)) / total_amount_origin
            )

        # Format as percentages for readability
        formatted_metrics = {
            k: f"{v * 100:.2f}%" if "rate" in k else v for k, v in metrics.items()
        }

        # 2. Get Logistics Data (Simplified for single store)
        # Purchase Plan
        purchase_data = self.client.get_purchase_plan(start_date, end_date)
        purchase_qty = 0
        for order in purchase_data:
            for item in order.get("items", []):
                if item.get("seller_name") == store_name:
                    purchase_qty += item.get("quantity_plan", 0)
        formatted_metrics["purchase_plan_qty"] = purchase_qty

        # Delivery Plan
        delivery_data = self.client.get_delivery_plan(start_date, end_date)
        delivery_qty = 0
        for record in delivery_data:
            for item in record.get("list", []):
                if item.get("sname") == canonical_store_name:
                    try:
                        delivery_qty += int(item.get("shipment_plan_quantity", 0))
                    except:
                        pass
        formatted_metrics["delivery_plan_qty"] = delivery_qty

        # FBA Out
        fba_out_data = self.client.get_fba_out(start_date, end_date)
        fba_out_qty = 0
        for record in fba_out_data:
            if (
                record.get("type_name") in ["FBA出库", "FBAM出库"]
                and record.get("store_name") == canonical_store_name
            ):
                fba_out_qty += abs(record.get("good_lock_num", 0))
        formatted_metrics["fba_actual_out_qty"] = fba_out_qty

        # 3. Inventory Turnover
        # FBA
        # FBA
        wid = PROJECT_WID.get(canonical_store_name)
        if wid:
            fba_inv = self.client.get_fba_inventory(
                f"{year}-{month:02d}", f"{year}-{month:02d}", wid
            )
            # Safe travel into nested dict
            summary = fba_inv.get("data", {}).get("summaryInfo")
            if isinstance(summary, dict):
                formatted_metrics["fba_turnover_days"] = summary.get("inventoryTurnoverDays", 0)

        # Local
        sid_id = PROJECT_SID.get(canonical_store_name)
        if sid_id:
            local_inv = self.client.get_local_inventory(start_date, end_date, sid_id)
            # Safe travel into nested dict and ensure data is not None
            data = local_inv.get("data")
            if isinstance(data, dict):
                total_info = data.get("total_info")
                if isinstance(total_info, dict):
                    formatted_metrics["local_turnover_days"] = total_info.get("rotation_day", 0)

        return formatted_metrics


def analyze_store(store_name: str, year: int = None, month: int = None):
    # 如果没传时间，默认查当前月份
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month

    client = LingXingClient()
    service = LingXingMetricsService(client)
    return service.get_store_cost_structure(store_name, year, month)
