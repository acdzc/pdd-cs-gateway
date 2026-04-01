"""
拼多多客服网关
"""

__version__ = "1.0.0"

# 拼多多客服 API 名称
PDD_API_CUSTOMER_SERVICE_SEND = "pdd.customer.service.message.send"
PDD_API_CUSTOMER_SERVICE_SESSION = "pdd.customer.service.session.get"
PDD_API_CUSTOMER_SERVICE_HISTORY = "pdd.customer.service.history.get"

# 订单相关 API
PDD_API_ORDER_INFO = "pdd.order.info.get"
PDD_API_LOGISTICS = "pdd.logistics.tracking.get"

# Webhook 消息类型
MSG_TYPE_CUSTOMER_SERVICE = "pdd_customer_service_message"
MSG_TYPE_ORDER_STATUS = "pdd_order_status_change"
MSG_TYPE_AFTER_SALE = "pdd_after_sale_status_change"