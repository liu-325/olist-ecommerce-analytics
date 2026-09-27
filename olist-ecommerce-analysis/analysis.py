import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

DATA = Path("data")

orders = pd.read_csv(DATA / "olist_orders_dataset.csv")
customers = pd.read_csv(DATA / "olist_customers_dataset.csv")
payments = pd.read_csv(DATA / "olist_order_payments_dataset.csv")
reviews = pd.read_csv(DATA / "olist_order_reviews_dataset.csv")
items = pd.read_csv(DATA / "olist_order_items_dataset.csv")
products = pd.read_csv(DATA / "olist_products_dataset.csv")
trans = pd.read_csv(DATA / "product_category_name_translation.csv")

orders["purchase_dt"] = pd.to_datetime(orders["order_purchase_timestamp"])
orders["delivered_dt"] = pd.to_datetime(orders["order_delivered_customer_date"])
orders["estimated_dt"] = pd.to_datetime(orders["order_estimated_delivery_date"])

pay = payments.groupby("order_id").agg(order_value=("payment_value", "sum")).reset_index()
base = orders.merge(customers, on="customer_id").merge(pay, on="order_id", how="left")

delivered = base[base.order_status == "delivered"].copy()
delivered["delivery_days"] = (delivered.delivered_dt - delivered.purchase_dt).dt.total_seconds() / 86400
delivered["late"] = delivered.delivered_dt.dt.normalize() > delivered.estimated_dt.dt.normalize()

print("orders", orders.order_id.nunique())
print("late rate", round(delivered.late.mean(), 4))

rev = reviews.groupby("order_id").review_score.mean().reset_index()
d = delivered.merge(rev, on="order_id", how="left")
print(d.groupby(d.review_score.round()).delivery_days.mean())

delivered["month"] = delivered.purchase_dt.dt.to_period("M").astype(str)
monthly = delivered.groupby("month").order_value.sum()
dec = monthly["2017-12"]
nov = monthly["2017-11"]
print("dec / nov", round(dec,2), round(nov,2), round((dec/nov-1)*100,2))

# 算出来才 3%，确实低
rep = delivered.groupby("customer_unique_id").order_id.nunique()
print("repeat rate", round((rep>1).mean(), 4))

# 先看下单次数分布
# delivered.groupby("customer_unique_id").order_id.nunique().value_counts()
# 大部分人就一单，复购确实低

# RFM 简单分层
rfm = delivered.groupby("customer_unique_id").agg(
    recency=("purchase_dt", lambda x: (delivered.purchase_dt.max() - x.max()).days),
    freq=("order_id", "nunique"),
    monetary=("order_value", "sum"),
)
# 分位数划档，5 档
rfm["r_score"] = pd.qcut(rfm.recency.rank(method="first"), 5, labels=[5,4,3,2,1]).astype(int)
rfm["f_score"] = pd.cut(rfm.freq, [0,1,2,3,999], labels=[1,2,3,5]).astype(int)
rfm["m_score"] = pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
rfm["seg"] = np.where((rfm.r_score>=4)&(rfm.m_score>=4), "high_recent_high_value",
             np.where((rfm.r_score<=2)&(rfm.m_score>=4), "high_value_low_active",
             np.where(rfm.freq>=2, "repeat", "other")))
print(rfm.seg.value_counts())
