---
title: TTS 回声消除：非流式 + discard 窗口跳过尾巴
category: patterns
source_projects: [hermes-desktop]
created: 2026-07-24
applicable_when: Push-to-talk 语音应用中 VAD 与 TTS 共存，TTS 播放声被 VAD 误识别为用户输入
not_applicable_when: 纯文本对话无语音输出，或 TTS 走外接扬声器且麦克风不会收到回声
token_saved_estimate: 600
tags: [tts, vad, echo-cancellation, voice, minimax]
---

## 背景
hermes-desktop v0.5.0 流式 TTS 有两个问题：(1) chunk 拼接处有 click 声；(2) VAD 会听到 TTS 播放尾巴，误触发新一轮收音。

## 做法
1. **切非流式 TTS**：MiniMax Speech-2.8-turbo 改非流式调用，整句生成后一次播放，消除 chunk 拼接 click
2. **设 discard 窗口**：TTS 播放结束后 300ms 内 VAD 收到的音频直接丢弃，跳过 TTS 回声尾巴
3. **保留人格一致性**：TTS 引擎切换不影响 Claude 老赫人格 prompt，只换声音合成层
4. **secrets.json 走 Rust env**：MiniMax API key 不落日志，Rust 侧读取后通过 invoke 传给前端

## 反例
- ❌ 流式 TTS + 无 discard 窗口 → chunk click 声 + VAD 自循环（TTS 说一句 → VAD 听到 → 再 ASR → 再回复 → 无限循环）
- ❌ discard 窗口设太长（如 1s）→ 用户快速追问时被丢弃，体验差
- ❌ discard 窗口设太短（如 100ms）→ TTS 尾巴的拖音仍被 VAD 捕获

## 验证
- 非流式 TTS 播放无 click 声（主观验收通过）
- TTS 播放结束后用户不说话 → VAD 不误触发
- TTS 播放结束后 300ms+ 用户说话 → VAD 正常捕获
- 老茅选定 `01_melo_female_speed10.wav` 音色，验收通过
