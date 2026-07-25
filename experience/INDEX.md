# 虚空藏经阁 - 经验库索引

> 由 extractor 自动维护。每条经验条目文件名格式：`YYYY-MM-DD-<slug>.md`
> 提炼自 `data/project_profiles/` 的行为画像，跨项目复用。

## 索引结构

| 分类 | 路径 | 用途 |
|---|---|---|
| patterns | `patterns/` | 解决问题模式（按问题类型：debug/perf/security/i18n/build/...） |
| prompts | `prompts/` | 高效提示词模板（按场景：code-review/architecture/refactor/...） |
| skills | `skills/` | 通用 skill 模板与使用经验 |
| mcp-usage | `mcp-usage/` | MCP 工具调用经验（lark/playwright/...） |
| failures | `failures/` | 失败案例（探路先遣队训练数据，含根因+教训） |

## 经验条目（按时间倒序）

<!-- EXTRACTOR_APPEND_BELOW_THIS_LINE -->
- [Tauri 凭据安全边界：Rust 侧读 + 白名单返回 + 禁日志](patterns/2026-07-24-tauri-凭据安全边界-rust-侧读---白名单返回---禁日志.md) (来源: hermes-desktop)
- [git_batch_commit_push MCP 工具：多根目录批量 git 操作](mcp-usage/2026-07-24-git_batch_commit_push-mcp-工具-多根目录批量-git-操作.md) (来源: hermes-desktop)
- [TTS 回声消除：非流式 + discard 窗口跳过尾巴](patterns/2026-07-24-tts-回声消除-非流式---discard-窗口跳过尾巴.md) (来源: hermes-desktop)
- [Sidecar 启动加速：引擎懒加载 + 后台预热](patterns/2026-07-24-sidecar-启动加速-引擎懒加载---后台预热.md) (来源: hermes-desktop)
- [Tauri 全局热键避开笔记本厂商保留键](patterns/2026-07-24-tauri-全局热键避开笔记本厂商保留键.md) (来源: hermes-desktop)
- [语音冷启动 ASR 首轮空转：诊断包先行 + 延迟修复决策](failures/2026-07-24-语音冷启动-asr-首轮空转-诊断包先行---延迟修复决策.md) (来源: hermes-desktop)
- [avatar skill 生图 drop-in 工作流：MJ 出图直接替换资源](skills/2026-07-24-avatar-skill-生图-drop-in-工作流-mj-出图直接替换资源.md) (来源: hermes-desktop)
- [VAD 伪全双工打断 + 300ms 回声消除窗口](patterns/2026-07-24-vad-伪全双工打断---300ms-回声消除窗口.md) (来源: hermes-desktop)
- [Sidecar 引擎懒加载 + 后台预热将启动时间从 15s 降至 0.5s](patterns/2026-07-24-sidecar-引擎懒加载---后台预热将启动时间从-15s-降至-0-5s.md) (来源: hermes-desktop)
- [Tauri webview 中 dangerouslyAllowBrowser 安全边界判定](patterns/2026-07-24-tauri-webview-中-dangerouslyallowbrowser-安全边界判定.md) (来源: hermes-desktop)
- [流式 TTS chunk 拼接产生 click 噪音](failures/2026-07-24-流式-tts-chunk-拼接产生-click-噪音.md) (来源: hermes-desktop)
- [笔记本 F8 键被厂商摄像头劫持导致语音热键失效](failures/2026-07-24-笔记本-f8-键被厂商摄像头劫持导致语音热键失效.md) (来源: hermes-desktop)


