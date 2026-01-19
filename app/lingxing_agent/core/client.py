import requests
from typing import List, Dict, Any, Optional
from app.lingxing_agent.core.auth import get_token


class LingXingClient:
    BASE_URL = "https://erp.lingxing.com"
    GW_URL = "https://gw.lingxingerp.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token if token else get_token()
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "ak-client-type": "web",
            "auth-token": self.token,
            "content-type": "application/json;charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "x-ak-company-id": "901217529031491584",
            "x-ak-env-key": "SAAS-101",
            "x-ak-platform": "1",
            "x-ak-request-source": "erp",
            "x-ak-uid": "10431785",  # From observed logs
            "x-ak-version": "3.7.1.3.0.004",
            "x-ak-zid": "10330128",
        }

    def _post(self, url: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(url, headers=self.headers, json=json_data)
        if response.status_code != 200:
            raise Exception(f"Request failed: {response.status_code} - {response.text}")
        return response.json()

    def _get(self, url: str) -> Dict[str, Any]:
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed: {response.status_code} - {response.text}")
        return response.json()

    def get_profit_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取按店铺聚合的利润报表数据"""
        url = f"{self.GW_URL}/bd/profit/report/report/seller/list"
        json_data = {
            "startDate": start_date,
            "endDate": end_date,
            "offset": 0,
            "length": 200,
            "mids": [],
            "sids": [],
            "currencyCode": "",
            "sellerPrincipalUids": [],
            "sortField": "totalSalesQuantity",
            "sortType": "desc",
            "isDisplayByDate": "month",
            "version": None,
            "listingTagIds": [],
            "isMonthly": True,
            "orderStatus": "DisbursedAndPreSettled",
            "transactionStatus": [],
            "req_time_sequence": "/bd/profit/report/report/seller/list$$13",
        }

        store_dict = {}
        offset = 0
        length = 200

        while True:
            json_data["offset"] = offset
            json_data["length"] = length

            data = self._post(url, json_data)
            fetched_records = data.get("data", {}).get("records", [])

            for order in fetched_records:
                store_name = order.get("storeName")
                if not store_name:
                    continue

                if store_name not in store_dict:
                    store_dict[store_name] = {}
                    for key, value in order.items():
                        if isinstance(value, (int, float)):
                            store_dict[store_name][key] = value
                        elif isinstance(value, str):
                            try:
                                store_dict[store_name][key] = float(value)
                            except (ValueError, TypeError):
                                store_dict[store_name][key] = value
                        else:
                            store_dict[store_name][key] = value
                else:
                    for key, value in order.items():
                        if isinstance(value, (int, float)):
                            store_dict[store_name][key] = (
                                store_dict[store_name].get(key, 0) + value
                            )
                        elif isinstance(value, str):
                            try:
                                num_value = float(value)
                                store_dict[store_name][key] = (
                                    store_dict[store_name].get(key, 0) + num_value
                                )
                            except (ValueError, TypeError):
                                pass

            if len(fetched_records) < length:
                break
            offset += length

        return list(store_dict.values())

    def get_purchase_plan(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取采购计划"""
        url = f"{self.BASE_URL}/api/purchase/planListsNew"
        json_data = {
            "offset": 0,
            "length": 200,
            "sort_field": "creator_time",
            "sort_type": "desc",
            "status": "-2",
            "country_code": [],
            "sids": [],
            "wids": [],
            "search_field_time": "creator_time",
            "search_field": "sku",
            "search_value": "",
            "senior_search_list": "[]",
            "start_date": start_date,
            "end_date": end_date,
            "req_time_sequence": "/api/purchase/planListsNew$$4",
        }

        all_data = []
        offset = 0
        length = 200

        while True:
            json_data["offset"] = offset
            json_data["length"] = length

            data = self._post(url, json_data)
            fetched_orders = data.get(
                "list", []
            )  # API response might be different, checking original code: data['list']
            # Original code: data = response.json(); fetched_orders = data['list']

            all_data.extend(fetched_orders)
            if len(fetched_orders) < length:
                break
            offset += length

        return all_data

    def get_delivery_plan(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取发货计划"""
        url = f"{self.BASE_URL}/api/fba_plan/planGroupList"
        json_data = {
            "receive_warehouse_type": "1",
            "search_field_time": "gmt_create",
            "start_date": start_date,
            "end_date": end_date,
            "offset": 0,
            "length": 200,
            "req_time_sequence": "/api/fba_plan/planGroupList$$2",
        }

        all_data = []
        offset = 0
        length = 200

        while True:
            json_data["offset"] = offset
            json_data["length"] = length

            data = self._post(url, json_data)
            # Original: data['data']['plan_list']
            fetched_orders = data.get("data", {}).get("plan_list", [])

            all_data.extend(fetched_orders)
            if len(fetched_orders) < length:
                break
            offset += length

        return all_data

    def get_fba_out(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取FBA出库数据"""
        url = f"{self.BASE_URL}/api/storage/statement"
        json_data = {
            "start_date": start_date,
            "end_date": end_date,
            "statement_type_list": "37,65",
            "offset": 0,
            "length": 200,
            "sort_field": "opt_time",
            "sort_type": "desc",
            "req_time_sequence": "/api/storage/statement$$6",
        }

        all_data = []
        offset = 0
        length = 200

        while True:
            json_data["offset"] = offset
            json_data["length"] = length

            data = self._post(url, json_data)
            # Original: data.get('data').get('list')
            fetched_orders = data.get("data", {}).get("list", [])

            all_data.extend(fetched_orders)
            if len(fetched_orders) < length:
                break
            offset += length

        return all_data

    def get_fba_inventory(
        self, start_date: str, end_date: str, wid: str
    ) -> Dict[str, Any]:
        """获取FBA库存周转数据"""
        url = f"{self.GW_URL}/cost/center/api/fba/gather/v2/query"
        json_data = {
            "dispositionType": "all",
            "orderDataType": "0",
            "startDate": start_date,
            "endDate": end_date,
            "wids": [wid],
            "uid": "10431785",
            "req_time_sequence": "/cost/center/api/fba/gather/v2/query$$3",
        }
        return self._post(url, json_data)

    def get_local_inventory(
        self, start_date: str, end_date: str, sid: str
    ) -> Dict[str, Any]:
        """获取本地库存周转数据"""
        url = f"{self.BASE_URL}/api/inventory_report/localQuantityDetailList"
        # GET request with query params
        query = f"filter_zero_storage=0&offset=0&length=20&start_date={start_date}&end_date={end_date}&sort_type=desc&sid_list={sid}&req_time_sequence=%2Fapi%2Finventory_report%2FlocalQuantityDetailList$$6"
        return self._get(f"{url}?{query}")
