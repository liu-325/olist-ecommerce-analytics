import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, average_precision_score

DATA = "data"
orders = pd.read_csv(f"{DATA}/olist_orders_dataset.csv")
customers = pd.read_csv(f"{DATA}/olist_customers_dataset.csv")
payments = pd.read_csv(f"{DATA}/olist_order_payments_dataset.csv")
items = pd.read_csv(f"{DATA}/olist_order_items_dataset.csv")
products = pd.read_csv(f"{DATA}/olist_products_dataset.csv")
sellers = pd.read_csv(f"{DATA}/olist_sellers_dataset.csv")
trans = pd.read_csv(f"{DATA}/product_category_name_translation.csv")

for c in ["order_purchase_timestamp","order_delivered_customer_date","order_estimated_delivery_date"]:
    orders[c] = pd.to_datetime(orders[c], errors="coerce")

df = orders[(orders.order_status=="delivered") & orders.order_delivered_customer_date.notna() & orders.order_estimated_delivery_date.notna()].copy()
# df.head()
# df.describe()
df["late"] = (df.order_delivered_customer_date.dt.normalize() > df.order_estimated_delivery_date.dt.normalize()).astype(int)
df["est_window"] = (df.order_estimated_delivery_date - df.order_purchase_timestamp).dt.days

pay = payments.groupby("order_id").agg(order_value=("payment_value","sum"), installments=("payment_installments","mean"), payment_type=("payment_type","first")).reset_index()
it = items.merge(products, on="product_id").merge(trans, on="product_category_name", how="left")
it["category"] = it.product_category_name_english.fillna(it.product_category_name)
it_agg = it.groupby("order_id").agg(item_count=("order_item_id","count"), product_count=("product_id","nunique"), seller_count=("seller_id","nunique"), total_price=("price","sum"), total_freight=("freight_value","sum"), avg_weight=("product_weight_g","mean"), avg_length=("product_length_cm","mean"), avg_height=("product_height_cm","mean"), avg_width=("product_width_cm","mean"), category=("category","first")).reset_index()

df = df.merge(customers[["customer_id","customer_unique_id","customer_state"]], on="customer_id").merge(pay, on="order_id", how="left").merge(it_agg, on="order_id", how="left")
so = df.merge(items[["order_id","seller_id"]].drop_duplicates(), on="order_id").merge(sellers[["seller_id","seller_state"]], on="seller_id", how="left")
so = so.sort_values(["seller_id","order_purchase_timestamp"])
so["same_state"] = (so.seller_state == so.customer_state).astype(int)

def rolling_stats(g):
    d = g.order_purchase_timestamp.values.astype("datetime64[ns]")
    late = g.late.to_numpy()
    n = len(g)
    prior_count = np.zeros(n)
    prior_late = np.zeros(n)
    cum = np.cumsum(late)
    for i in range(n):
        j = np.searchsorted(d, d[i]-np.timedelta64(90,"D"), side="left")
        prior_count[i] = i - j
        prior_late[i] = cum[i] - cum[j]
    g = g.copy()
    g["seller_late_rate"] = prior_late / np.maximum(prior_count,1)
    g["seller_prior_count"] = prior_count
    return g

so = so.groupby("seller_id", group_keys=False).apply(rolling_stats)
grp = so.groupby("order_id").agg(seller_late_rate=("seller_late_rate","mean"), seller_prior_count=("seller_prior_count","mean"), seller_state_n=("seller_state","nunique"), same_state_share=("same_state","mean"), seller_state=("seller_state","first")).reset_index()
df = df.merge(grp, on="order_id", how="left")
df["hour"] = df.order_purchase_timestamp.dt.hour
df["weekday"] = df.order_purchase_timestamp.dt.weekday
df["month"] = df.order_purchase_timestamp.dt.month
df["freight_ratio"] = df.total_freight / (df.total_price + 1)

features = ["order_value","installments","item_count","product_count","seller_count","total_price","total_freight","avg_weight","avg_length","avg_height","avg_width","est_window","hour","weekday","month","seller_late_rate","seller_prior_count","seller_state_n","same_state_share","freight_ratio"]
cats = ["payment_type","category","customer_state","seller_state"]

# 一开始随机切的，后来想了想不行——预测未来不能用未来数据
cut = pd.Timestamp("2018-04-01")
train = df[df.order_purchase_timestamp < cut]
test = df[df.order_purchase_timestamp >= cut]
print(train.shape, test.shape, test.late.mean())

# product_weight_g 有几个空值，量小，先中位数填了
for c in features:
    train[c] = train[c].fillna(train[c].median())
    test[c] = test[c].fillna(train[c].median())
for c in cats:
    train[c] = train[c].fillna("unknown")
    test[c] = test[c].fillna("unknown")

pre = ColumnTransformer([("num", StandardScaler(), features), ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=5), cats)])
model = Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42))])
model.fit(train[features+cats], train.late)
prob = model.predict_proba(test[features+cats])[:,1]
top = prob >= np.quantile(prob, .8)
print("auc", roc_auc_score(test.late, prob))
print("pr_auc", average_precision_score(test.late, prob))
print("top20_rate", test.late[top].mean(), "lift", test.late[top].mean()/test.late.mean())

# XGBoost 这边过拟合了，train 0.9 测试 0.7，算了用逻辑回归
