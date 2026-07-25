# failures/ - 失败案例（探路先遣队训练数据）

存放项目失败案例，作为「探路先遣队」训练数据。失败是最高价值的经验来源。

## 失败类型
- approach-failed：方案失败（选错技术栈/架构）
- time-overflow：72h MVA 超时未达成
- token-waste：token 浪费严重
- security-incident：安全事故（含密钥泄露等）
- user-kill：用户主动 Kill 项目

## 条目格式
见 `templates/experience_template.md`（category 字段填 `failures`）

## 特别字段
失败案例必须包含：
- **根因**：为什么失败
- **教训**：下次怎么避免
- **可回收资产**：失败中产生的可复用代码/文档/工具
