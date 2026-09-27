# Olist 电商经营分析

巴西电商 Olist 的公开数据集，8 张表、约 10 万订单。想搞清楚两件事：GMV 为什么 12 月掉了一截，以及哪些客户值得召回。

数据：[Kaggle brazilian-ecommerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

做了什么：

- 8 张表导入 SQLite，统一 GMV / 复购率 / 延迟交付率口径
- 2017 年 12 月 GMV 环比掉 26.9%，剔除黑五后定位到新客在圣保罗州家居床品类目
- RFM 分层发现复购率只有 3%，圈出 1.46 万高价值低活跃客户
- RJ 州延迟率 12.11%，1 星订单平均比 5 星晚 10.66 天

结论：先治物流，再做召回，看板用 Power BI 搭了三页。
