"""
测试消息处理器
"""
import pytest
from app.pdd.message_handler import IntentClassifier, IntentType


class TestIntentClassifier:
    """意图分类器测试"""

    def test_order_query(self):
        """测试订单查询意图"""
        assert IntentClassifier.classify("我的订单到哪了") == IntentType.ORDER_QUERY
        assert IntentClassifier.classify("订单号123456789") == IntentType.ORDER_QUERY
        assert IntentClassifier.classify("什么时候发货") == IntentType.ORDER_QUERY

    def test_logistics_query(self):
        """测试物流查询意图"""
        assert IntentClassifier.classify("快递到哪了") == IntentType.LOGISTICS_QUERY
        assert IntentClassifier.classify("物流信息") == IntentType.LOGISTICS_QUERY
        assert IntentClassifier.classify("什么时候到") == IntentType.LOGISTICS_QUERY

    def test_product_query(self):
        """测试商品咨询意图"""
        assert IntentClassifier.classify("这个有货吗") == IntentType.PRODUCT_QUERY
        assert IntentClassifier.classify("多少钱") == IntentType.PRODUCT_QUERY
        assert IntentClassifier.classify("有什么颜色") == IntentType.PRODUCT_QUERY

    def test_after_sale(self):
        """测试售后意图"""
        assert IntentClassifier.classify("我要退货") == IntentType.AFTER_SALE
        assert IntentClassifier.classify("质量问题") == IntentType.AFTER_SALE
        assert IntentClassifier.classify("坏了") == IntentType.AFTER_SALE

    def test_complaint(self):
        """测试投诉意图"""
        assert IntentClassifier.classify("我要投诉") == IntentType.COMPLAINT
        assert IntentClassifier.classify("骗子") == IntentType.COMPLAINT

    def test_human_takeover(self):
        """测试人工接管关键词"""
        assert IntentClassifier.need_human_takeover("转人工", ["人工", "转人工"]) == True
        assert IntentClassifier.need_human_takeover("我要人工客服", ["人工"]) == True
        assert IntentClassifier.need_human_takeover("你好", ["人工"]) == False

    def test_general(self):
        """测试一般咨询"""
        assert IntentClassifier.classify("你好") == IntentType.GENERAL
        assert IntentClassifier.classify("在吗") == IntentType.GENERAL