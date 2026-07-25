---
title: 流式 TTS chunk 拼接产生 click 噪音
category: failures
source_projects: [hermes-desktop]
created: 2026-07-24
applicable_when: 使用流式 TTS API（MiniMax / Azure / 火山）按 chunk 返回音频并在前端拼接播放
not_applicable_when: 使用纯本地 TTS（sherpa-onnx VITS）无 chunk 边界问题；TTS 回复极短（<50 字）无感知延迟
token_saved_estimate: 5000
tags: [tts, streaming, audio, minimax, click-noise]
---

## 背景
hermes-desktop v0.5.0 用 MiniMax Speech-2.8-turbo 流式 TTS，前端收到多个 chunk 后用 AudioBuffer 顺序拼接播放。每个 chunk 边界处产生 click 噪音，老茅听感极差。

## 做法
1. **切非流式**：对商用 TTS API 直接用非流式端点，一次请求拿完整音频。延迟增加 200-500ms 但无拼接瑕疵。
2. **流式场景必须加交叉淡入淡出**：每个 chunk 末尾 5ms 线性 fade-out，下一个 chunk 开头 5ms fade-in，用 WebAudio `gainNode` 实现。
3. **chunk 对齐到句子边界**：sidecar 侧按句号/问号/感叹号切句，每句一个 TTS 请求，自然消除 chunk 中间断裂。

## 反例
直接把流式 chunk 的 PCM 数据 `memcpy` 拼接后播放。后果：每秒 1-2 次 click 杂音，用户无法正常使用。

## 验证
用 Audacity 录制输出音频，频谱图上 chunk 边界处无尖峰。老茅主观验收通过。
