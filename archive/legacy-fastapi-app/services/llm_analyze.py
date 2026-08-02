"""
LLM analysis service — calls external LLM APIs (SiliconFlow / Ollama / Zhipu).
Resolves Bug #5: API Key is managed server-side, not passed from frontend.
Uses httpx for async HTTP calls with timeout support (Bug #11 fix).
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.exceptions import LLMAnalysisError
from app.core.logging import get_logger
from app.core.security import APIKeyManager
from app.config import get_settings

log = get_logger("llm_analyze")

# Provider API base URLs
PROVIDER_BASE_URLS = {
    "siliconflow": "https://api.siliconflow.cn/v1",
    "ollama": "http://localhost:11434/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
}

# Default models per provider
PROVIDER_DEFAULT_MODELS = {
    "siliconflow": "Qwen/Qwen2.5-7B-Instruct",
    "ollama": "llama3.1",
    "zhipu": "glm-4-flash",
}


def _get_api_key(provider: str) -> str:
    """Get the API key for the specified provider from server-side config."""
    settings = get_settings()

    # For ollama, no API key needed
    if provider == "ollama":
        return ""

    # Use the server-configured key
    key = settings.llm_api_key
    if not key:
        raise LLMAnalysisError(
            f"No API key configured for provider '{provider}'",
            provider=provider,
        )
    return key


def _get_base_url(provider: str) -> str:
    """Get the API base URL for the specified provider."""
    settings = get_settings()
    if provider == "siliconflow" and settings.llm_base_url:
        return settings.llm_base_url
    return PROVIDER_BASE_URLS.get(provider, PROVIDER_BASE_URLS["siliconflow"])


def _build_analysis_prompt(
    transcription: dict[str, Any],
    analysis: dict[str, Any],
    video_meta: dict[str, Any],
) -> str:
    """Build the LLM prompt for deep content analysis."""
    prompt = f"""你是一位专业的内容分析师，请基于以下视频分析数据，按照"5位一体方法论"生成九节结构化深度分析报告。

## 方法论框架
1. 叙事主权利破局
2. 反资共情
3. 5A人群流转 (Aware/Appeal/Ask/Act/Advocate)
4. 实效卖点种草
5. 信任建立体系

## 视频元数据
- 分辨率: {video_meta.get('width', '?')}x{video_meta.get('height', '?')}
- 帧率: {video_meta.get('fps', '?')}fps
- 时长: {transcription.get('duration', '?')}秒

## 语音转写文本
{transcription.get('text', '无音频内容')}

## 转写分段
{json.dumps(transcription.get('segments', []), ensure_ascii=False, indent=2)[:3000]}

## 关键词
{json.dumps(transcription.get('keywords', {}), ensure_ascii=False, indent=2)}

## 画面分析摘要
- 内容类型: {analysis.get('content_type', '未知')}
- 平均亮度: {analysis.get('avg_brightness', '?')}
- 平均运动强度: {analysis.get('avg_motion', '?')}
- 场景切换次数: {analysis.get('scene_changes', '?')}

## 输出要求
请按照以下九节结构生成报告，每节至少200字：

### 第一节：叙事主权利破局
### 第二节：反资共情策略
### 第三节：5A人群流转分析
### 第四节：实效卖点种草
### 第五节：信任建立体系
### 第六节：内容结构拆解
### 第七节：画面与文案协同分析
### 第八节：优化建议
### 第九节：总结与核心洞察
"""
    return prompt


async def test_api_key(provider: str, api_key: str, base_url: str | None = None) -> dict:
    """
    Test an API key by listing available models.

    Args:
        provider: LLM provider name.
        api_key: API key to test.
        base_url: Optional custom base URL.

    Returns:
        Dict with 'valid' (bool) and 'models' (list of model names).
    """
    url = base_url or _get_base_url(provider)
    headers = {"Authorization": f"Bearer {api_key}"}

    log.info("testing_api_key", provider=provider, key_masked=APIKeyManager.mask(api_key))

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{url}/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", [])]
                return {"valid": True, "models": models}
            else:
                return {"valid": False, "models": [], "error": resp.text}
    except Exception as e:
        return {"valid": False, "models": [], "error": str(e)}


async def analyze_content(
    transcription: dict[str, Any],
    analysis: dict[str, Any],
    video_meta: dict[str, Any],
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """
    Call LLM API to generate deep content analysis.

    Args:
        transcription: Transcription data (text, segments, keywords).
        analysis: Video frame analysis results.
        video_meta: Video metadata (width, height, fps).
        model: LLM model name. Uses default if not specified.
        provider: LLM provider. Uses configured default if not specified.

    Returns:
        Dict with 'report' (markdown text), 'model_used', 'tokens_used'.

    Raises:
        LLMAnalysisError: If the LLM API call fails.
    """
    settings = get_settings()
    provider = provider or settings.llm_provider
    api_key = _get_api_key(provider)
    base_url = _get_base_url(provider)
    model = model or PROVIDER_DEFAULT_MODELS.get(provider, settings.llm_default_model)

    prompt = _build_analysis_prompt(transcription, analysis, video_meta)

    log.info(
        "starting_llm_analysis",
        provider=provider,
        model=model,
        key_masked=APIKeyManager.mask(api_key) if api_key else "none",
    )

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一位专业的内容分析师和文案专家。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.llm_request_timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

            if resp.status_code != 200:
                error_detail = resp.text[:500]
                log.error(
                    "llm_api_error",
                    status=resp.status_code,
                    detail=error_detail,
                    provider=provider,
                )
                raise LLMAnalysisError(
                    f"LLM API returned {resp.status_code}: {error_detail}",
                    provider=provider,
                )

            data = resp.json()
            report = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            log.info(
                "llm_analysis_complete",
                provider=provider,
                model=model,
                tokens=tokens_used,
                report_length=len(report),
            )

            return {
                "report": report,
                "model_used": model,
                "tokens_used": tokens_used,
            }

    except httpx.TimeoutException:
        raise LLMAnalysisError(
            f"LLM API request timed out after {settings.llm_request_timeout}s",
            provider=provider,
        )
    except httpx.ConnectError as e:
        raise LLMAnalysisError(
            f"Cannot connect to LLM API: {e}",
            provider=provider,
        )
