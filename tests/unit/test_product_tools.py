"""
Unit tests for app.lingxing_agent.tools.product_tools

Tests:
1. check_product_status - various purchase/shipment scenarios
2. get_product_performance - performance data retrieval
"""
import pytest
from unittest.mock import patch, MagicMock


# ==================== Test check_product_status ====================

class TestCheckProductStatus:
    """Tests for check_product_status tool."""

    @patch('app.lingxing_agent.tools.product_tools.api_client')
    def test_purchase_completed_normal_shipment(self, mock_client):
        """测试：采购已完成 + 正常发货"""
        from app.lingxing_agent.tools.product_tools import check_product_status
        
        # Mock purchase data - 采购已到达
        mock_client.request_web_purchasedate.return_value = {
            'data': {
                'list': [{
                    'quantity_entry': 100,
                    'status_text': '已完成',
                    'order_time': '2024-01-01 10:00:00',
                    'finish_time': '2024-01-10 10:00:00',
                    'item_list': [{'seller_name': 'Amazon US'}]
                }]
            }
        }
        
        # Mock delivery data - 有发货记录
        mock_client.request_deliver_page.return_value = {
            'data': {
                'list': [{
                    'total_quantity_shipped': 50,
                    'shipment_time': '2024-01-15 10:00:00',
                    'relate_list': [{'sname': 'Amazon US'}]
                }]
            }
        }
        
        result = check_product_status('TEST-MSKU-001', 'Amazon US')
        
        assert result['status'] == '正常发货'
        assert result['purchase_status'] == '采购已到达'
        assert result['is_borrowed'] == False
        assert result['initial_stock_num'] == 50

    @patch('app.lingxing_agent.tools.product_tools.api_client')
    def test_no_purchase_borrowed_shipment(self, mock_client):
        """测试：无采购记录 + 借调发货"""
        from app.lingxing_agent.tools.product_tools import check_product_status
        
        # Mock - 无采购数据
        mock_client.request_web_purchasedate.return_value = {'data': {'list': []}}
        mock_client.request_web_processing_purchasedate.return_value = {'list': []}
        
        # Mock - 有发货记录
        mock_client.request_deliver_page.return_value = {
            'data': {
                'list': [{
                    'total_quantity_shipped': 30,
                    'shipment_time': '2024-01-15 10:00:00',
                    'relate_list': [{'sname': 'Amazon US'}]
                }]
            }
        }
        
        result = check_product_status('TEST-MSKU-002', 'Amazon US')
        
        assert result['status'] == '借调发货'
        assert result['is_borrowed'] == True
        assert result['initial_stock_num'] == 30

    @patch('app.lingxing_agent.tools.product_tools.api_client')
    def test_purchase_not_arrived(self, mock_client):
        """测试：采购已下单但未到达"""
        from app.lingxing_agent.tools.product_tools import check_product_status
        
        mock_client.request_web_purchasedate.return_value = {
            'data': {
                'list': [{
                    'quantity_entry': 100,
                    'status_text': '待到货',
                    'order_time': '2024-01-01 10:00:00',
                    'finish_time': '-',  # 未完成
                    'item_list': [{'seller_name': 'Amazon US'}]
                }]
            }
        }
        mock_client.request_deliver_page.return_value = {'data': {'list': []}}
        
        result = check_product_status('TEST-MSKU-003', 'Amazon US')
        
        assert result['status'] == '采购已下单，未到达'
        assert result['purchase_status'] == '采购未到达'

    @patch('app.lingxing_agent.tools.product_tools.api_client')
    def test_processing_product(self, mock_client):
        """测试：加工产品的采购状态"""
        from app.lingxing_agent.tools.product_tools import check_product_status
        
        # Mock - 普通采购无数据
        mock_client.request_web_purchasedate.return_value = {'data': {'list': []}}
        
        # Mock - 加工采购有数据
        mock_client.request_web_processing_purchasedate.return_value = {
            'data': {
                'list': [{
                    'status': 1,  # Not cancelled
                    'create_time': '2024-01-01 10:00:00',
                    'finish_time': '2024-01-05 10:00:00',
                    'product_list': [{'seller_name': 'Amazon US'}]
                }]
            }
        }
        mock_client.request_deliver_page.return_value = {'data': {'list': []}}
        
        result = check_product_status('PROCESS-MSKU-001', 'Amazon US', is_processing=True)
        
        assert result['purchase_status'] == '采购已到达'


# ==================== Test get_product_performance ====================

class TestGetProductPerformance:
    """Tests for get_product_performance tool."""

    @patch('app.lingxing_agent.tools.product_tools.api_client')
    def test_performance_data_found(self, mock_client):
        """测试：正常获取产品表现数据"""
        from app.lingxing_agent.tools.product_tools import get_product_performance
        
        mock_client.get_product_performance.return_value = {
            'data': {
                'records': [{
                    'msku': 'TEST-MSKU-001',
                    'asin': 'B08XXXXX',
                    'storeName': 'Amazon US',
                    'volume': 150,
                    'totalFbaAndFbmAmount': 5000.50,
                    'orderCount': 120,
                    'grossProfit': 1500.25,
                    'grossProfitRate': 0.30,
                    'totalAdsCost': 200.00,
                    'acos': 0.04,
                    'tacos': 0.05,
                    'fbaInventory': 500,
                    'sellableDays': 30
                }]
            }
        }
        
        result = get_product_performance('TEST-MSKU-001', '2024-01-01', '2024-01-31')
        
        assert result['msku'] == 'TEST-MSKU-001'
        assert result['volume'] == 150
        assert result['sales_amount'] == 5000.50
        assert result['gross_profit'] == 1500.25
        assert result['total_ads_cost'] == 200.00
        assert result['fba_inventory'] == 500

    @patch('app.lingxing_agent.tools.product_tools.api_client')
    def test_performance_data_not_found(self, mock_client):
        """测试：未找到产品表现数据"""
        from app.lingxing_agent.tools.product_tools import get_product_performance
        
        mock_client.get_product_performance.return_value = {'data': {'records': []}}
        
        result = get_product_performance('NONEXISTENT-MSKU')
        
        assert 'error' in result
        assert result['msku'] == 'NONEXISTENT-MSKU'

    @patch('app.lingxing_agent.tools.product_tools.api_client')
    def test_performance_default_dates(self, mock_client):
        """测试：默认日期范围（本月）"""
        from app.lingxing_agent.tools.product_tools import get_product_performance
        from datetime import datetime
        
        mock_client.get_product_performance.return_value = {
            'data': {'records': [{'msku': 'TEST', 'volume': 10}]}
        }
        
        result = get_product_performance('TEST')
        
        # Verify the default dates were used
        expected_start = datetime.now().strftime("%Y-%m-01")
        expected_end = datetime.now().strftime("%Y-%m-%d")
        assert result['start_date'] == expected_start
        assert result['end_date'] == expected_end


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
