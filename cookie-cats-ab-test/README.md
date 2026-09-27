# Cookie Cats A/B 测试

手游 Cookie Cats 想把第一道卡点从 30 级移到 40 级。这个实验判断改完后玩家留存会不会更好。

数据：Kaggle 的 Mobile Games A/B Testing - Cookie Cats，90,189 名玩家。

做了什么：

- 先看两组样本量有没有偏差
- 用双样本比例检验比较 1 日和 7 日留存
- 对游戏局数做了 log、截尾均值和 Mann-Whitney U
- 7 日留存 gate_30 19.02%，gate_40 18.20%，p=0.0016

结论：改到 40 级没有带来参与度提升，7 日留存还更低，建议保留 30 级。
