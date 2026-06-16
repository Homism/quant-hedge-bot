# V2 只读量化看板

Unified Dashboard V2 是 BTC / ETH / SOL / XAUT dry-run 机器人的只读量化监控页。
它用于观察模拟盘状态，不负责下单，也不修改机器人配置。

## 安全边界

Dashboard 只读，禁止做这些事：

- 下单
- 平仓
- 撤单
- 改杠杆
- 修改策略
- 修改配置
- 修改 `dry_run`
- 启用 live trading

Dashboard 后端只提供 `GET /api/summary`，并拒绝 `POST`、`PUT`、`DELETE`。
页面中不包含交易按钮。

## 本地端口

Dashboard 只绑定 localhost：

```text
127.0.0.1:8090
```

VPS 上不要把 8090 暴露到公网。

## SSH Tunnel 访问

在 Mac 上打开 Dashboard：

```bash
ssh -i ~/.ssh/ovh_vps_ac72a73f -L 8090:127.0.0.1:8090 ubuntu@148.113.191.170
```

然后浏览器打开：

```text
http://127.0.0.1:8090
```

如果要同时打开 4 个 Freqtrade UI：

```bash
ssh -i ~/.ssh/ovh_vps_ac72a73f \
  -L 8081:127.0.0.1:8081 \
  -L 8082:127.0.0.1:8082 \
  -L 8083:127.0.0.1:8083 \
  -L 8084:127.0.0.1:8084 \
  -L 8090:127.0.0.1:8090 \
  ubuntu@148.113.191.170
```

## V2 显示内容

顶部总览：

- 机器人总数
- 在线机器人数量
- 是否全部在线机器人都是 dry-run
- 总模拟盈亏
- 今日总模拟盈亏
- 当前总持仓数
- 今日平仓数
- 最佳模拟交易
- 最差模拟交易
- 最大回撤，如果 Freqtrade API 返回该数据
- 是否触发风控
- 是否有机器人离线

每个 bot 卡片显示：

- 在线状态
- dry-run 状态
- 交易对
- 当前价格
- 24 小时涨跌
- 24 小时成交量
- 资金费率，如果公开行情接口返回该数据
- 最近 K 线时间
- EMA20
- EMA50
- RSI
- 20 根成交量均值
- 当前是否满足做空入场条件
- 当前是否满足退出条件
- 为什么开仓或为什么不开仓
- 模拟交易记录
- 风控详情
- 最近错误

XAUT 卡片额外显示：

- XAUT futures validation 状态
- XAUT bot 是否启动
- 当前交易所模板
- Binance XAUT 价格
- OKX XAUT 价格，如果公开接口可用
- 价差百分比占位，用于后续 spread monitor

## 数据来源

- Freqtrade REST API：只读读取 bot 状态、配置、PnL、交易记录和日志。
- Binance/OKX public API：只读读取行情、K 线、资金费率和 XAUT 价格。
- 本地文件：只读检查 kill switch 状态。

这些数据源不需要交易所 API Key。Dashboard 不读取私钥，不连接钱包，不做链上签名或广播。
