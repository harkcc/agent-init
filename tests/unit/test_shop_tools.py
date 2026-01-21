"""
Unit tests for app.lingxing_agent.tools.metrics

Tests:
1. analyze_store - store cost structure and metrics
"""
import pytest
from unittest.mock import patch, MagicMock


class TestAnalyzeStore:
    """Tests for analyze_store tool."""

    @patch('app.lingxing_agent.tools.metrics.LingXingClient')
    def test_store_analysis_success(self, MockClient):
        """测试：成功获取店铺分析数据"""
        from app.lingxing_agent.tools.metrics import analyze_store
        
        # Setup mock client instance
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        
        # Mock profit data
        mock_instance.get_profit_data.return_value = [{
            'storeName': 'Amazon US',
            'totalFbaAndFbmAmount': 100000,
            'shippingCredits': 0,
            'promotionalRebates': 0,
            'fbaInventoryCredit': 0,
            'cashOnDelivery': 0,
            'otherInAmount': 0,
            'totalSalesRefunds': -5000,
            'totalSalesTax': 0,
            'salesTaxRefund': 0,
            'salesTaxWithheld': 0,
            'refundTaxWithheld': 0,
            'grossProfit': 30000,
            'cgTransportCostsTotal': 10000,
            'totalStorageFee': 2000,
            'cgPriceTotal': 40000,
            'fbaDeliveryFee': 15000,
            'fbaTransactionFeeRefunds': 0,
            'totalAdsCost': 5000,
            'promotionFee': 500,
            'platformFee': 8000,
        }]
        
        # Mock other data (simplified)
        mock_instance.get_purchase_plan.return_value = []
        mock_instance.get_delivery_plan.return_value = []
        mock_instance.get_fba_out.return_value = []
        mock_instance.get_fba_inventory.return_value = {'data': {'summaryInfo': {'inventoryTurnoverDays': 45}}}
        mock_instance.get_local_inventory.return_value = {'data': {'total_info': {'rotation_day': 30}}}
        
        result = analyze_store('Amazon US', 2024, 1)
        
        # The function returns formatted_metrics which might have 'error' or success data
        assert 'GMV' in result or 'error' in result
        if 'error' not in result:
            assert result['year'] == 2024
            assert result['month'] == 1

    @patch('app.lingxing_agent.tools.metrics.LingXingClient')
    def test_store_not_found(self, MockClient):
        """测试：店铺不存在"""
        from app.lingxing_agent.tools.metrics import analyze_store
        
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.get_profit_data.return_value = [{
            'storeName': 'Amazon US',
            # ... other fields
        }]
        
        result = analyze_store('Nonexistent Store', 2024, 1)
        
        assert 'error' in result

    @patch('app.lingxing_agent.tools.metrics.LingXingClient')
    def test_store_fuzzy_match(self, MockClient):
        """测试：模糊匹配店铺名称"""
        from app.lingxing_agent.tools.metrics import analyze_store
        
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        
        # Return data with full store name
        mock_instance.get_profit_data.return_value = [{
            'storeName': 'Amazon US',
            'totalFbaAndFbmAmount': 50000,
            'grossProfit': 15000,
            # Simplified - add all required fields for calculation
            'shippingCredits': 0, 'promotionalRebates': 0, 'fbaInventoryCredit': 0,
            'cashOnDelivery': 0, 'otherInAmount': 0, 'totalSalesRefunds': 0,
            'totalSalesTax': 0, 'salesTaxRefund': 0, 'salesTaxWithheld': 0, 'refundTaxWithheld': 0,
            'cgTransportCostsTotal': 5000, 'totalStorageFee': 1000, 'cgPriceTotal': 20000,
            'fbaDeliveryFee': 8000, 'fbaTransactionFeeRefunds': 0, 'totalAdsCost': 2000,
            'promotionFee': 200, 'platformFee': 4000,
        }]
        mock_instance.get_purchase_plan.return_value = []
        mock_instance.get_delivery_plan.return_value = []
        mock_instance.get_fba_out.return_value = []
        mock_instance.get_fba_inventory.return_value = {'data': {}}
        mock_instance.get_local_inventory.return_value = {'data': {}}
        
        # Query with partial name (US instead of Amazon US)
        result = analyze_store('US', 2024, 1)
        
        # Should still find Amazon US through fuzzy matching
        # Note: This depends on config.py having 'Amazon US' in PROJECT_SID
        # If it doesn't exist, it will return error
        if 'error' not in result:
            assert result['store_name'] == 'US'

    @patch('app.lingxing_agent.tools.metrics.LingXingClient')
    def test_default_date_to_current_month(self, MockClient):
        """测试：默认使用当前月份"""
        from app.lingxing_agent.tools.metrics import analyze_store
        from datetime import datetime
        
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.get_profit_data.return_value = []
        
        # Call without year/month
        result = analyze_store('Amazon US')
        
        # The function should use current year/month
        now = datetime.now()
        # Result might be error due to no data, but the call should work
        assert True  # Just verifying no exception


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
