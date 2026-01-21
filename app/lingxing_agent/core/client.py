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

    def request_web_purchasedate(self, sku: str) -> Dict[str, Any]:
        """获取采购信息:非加工 (对应 request_web_purchasedate)"""
        # URL: https://erp.lingxing.com/api/purchase/orderListsV2
        json_data = {
            'offset': 0, 'length': 200, 
            'expect_arrive_time_status': '',
            'alibaba_amount_is_diff': '',
            'sort_field': 'create_time', 'sort_type': 'desc',
            'status_shipped': [], 'status': '', 'pay_status': [],
            'search_field_time': 'pay_time', 'search_field': 'sku', 'search_value': sku,
            'wid': [], 'sid': [], 'purchaser_id': [], 'cg_uids': [],
            'sub_status_list': [], 'logistics_status_list_1688': [],
            'gtag_ids': '', 'permission_uid_list': [], 'senior_search_list': [],
            'is_urgent': '', 'change_order_status': '', 'notice_receipt': '',
            'is_bad': '', 'is_tax': '', 'is_logistics': '',
            'is_associate_return': 0, 'is_associate_exchange': 0,
            'req_time_sequence': '/api/purchase/orderListsV2$$7',
        }
        return self._post(f"{self.BASE_URL}/api/purchase/orderListsV2", json_data)

    def request_oversea_plan(self, sku: str) -> Dict[str, Any]:
        """获取发货/海外仓计划 (对应 request_web_multi_sku_shiptitme)"""
        # URL: https://erp.lingxing.com/api/oversea_plan/planGroupList
        json_data = {
            'receive_warehouse_type': '3',
            'status': '',
            'create_uids': [], 'audit_uids': [],
            'is_relate_purchase': '', 'is_relate_process': '',
            'spo_status': [], 'is_relate_overseas': '',
            'is_relate_packing_task_sn': '', 'lock_status': '',
            'ship_mode': '', 'is_urgent': '',
            'search_field_time': 'gmt_create', 'search_field': 'sku', 'search_value': sku,
            'seniorSearchList': [],
            'offset': 0, 'length': 200,
            'req_time_sequence': '/api/oversea_plan/planGroupList$$5',
        }
        return self._post(f"{self.BASE_URL}/api/oversea_plan/planGroupList", json_data)

    def request_deliver_page(self, msku: str) -> Dict[str, Any]:
        """获取发货单查询 (保留原有的, 对应 request_deliver_page)"""
        json_data = {
             'offset': 0, 'length': 20, 'sort_field': 'create_time', 'sort_type': 'desc',
             'search_field': 'msku', 'search_value': msku,
             'req_time_sequence': '/api/fba/shipment_plan/lists$$15'
        }
        return self._post(f"{self.BASE_URL}/api/fba/shipment_plan/lists", json_data)

    def get_product_performance(self, start_date: str, end_date: str, msku: str = None) -> Dict[str, Any]:
        """获取产品表现数据 (销量、销售额、广告等)"""
        json_data = {
            'sort_field': 'volume',
            'sort_type': 'desc',
            'offset': 0,
            'length': 200, # Limit for single query
            'search_field': 'msku',
            'search_value': [msku] if msku else [],
            'mids': '',
            'sids': '',
            'date_type': 'purchase',
            'start_date': start_date,
            'end_date': end_date,
            'principal_uids': [],
            'bids': [],
            'cids': [],
            'extend_search': [],
            'summary_field': 'msku',
            'currency_code': '',
            'product_states': [],
            'is_resale': '',
            'order_types': [],
            'promotions': [],
            'developers': [],
            'delivery_methods': [],
            'is_recently_enum': True,
            'ad_cost_type': '',
            'attr_value_ids': [],
            'turn_on_summary': 1,
            'summary_field_level1': '',
            'summary_field_level2': '',
            'gtag_ids': [],
            'sub_summary_type': 'msku',
            'regions': [],
            'date_range_type': 0,
            'req_time_sequence': '/bd/productPerformance/asinLists$$19',
        }
        return self._post(f"{self.GW_URL}/bd/productPerformance/asinLists", json_data)


