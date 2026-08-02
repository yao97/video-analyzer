"""
Text processing utilities — keyword extraction and text analysis.
Extracts high-frequency words, action verbs, emotion words, and product terms
from transcription text.
"""
from __future__ import annotations

import re
from collections import Counter

# Chinese stop words (common words to filter out)
STOP_WORDS = {
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "那", "它", "他", "她", "们", "这个", "那个", "什么", "怎么",
    "可以", "就是", "还是", "因为", "所以", "但是", "如果", "虽然", "然后", "不过",
    "一下", "一些", "这样", "那样", "这里", "那里", "觉得", "现在", "已经", "可能",
}

# Action verbs commonly used in content
ACTION_WORDS = {
    "推荐", "介绍", "讲解", "分享", "展示", "演示", "说明", "告诉", "教", "带",
    "看", "来", "做", "用", "试", "买", "选", "挑", "搭", "配",
}

# Emotion words
EMOTION_WORDS = {
    "非常", "特别", "真的", "喜欢", "完美", "太", "超", "极", "最", "棒",
    "好", "赞", "爱", "惊", "哇", "牛", "厉害", "不错", "值得", "推荐",
}


def extract_keywords(text: str, top_n: int = 20) -> dict[str, list[str]]:
    """
    Extract keywords from text, categorized into four types.

    Args:
        text: Input text to analyze.
        top_n: Maximum number of keywords per category.

    Returns:
        Dict with keys: highFreq, actions, emotions, products.
    """
    if not text:
        return {"highFreq": [], "actions": [], "emotions": [], "products": []}

    # Extract Chinese words (2-4 character sequences)
    chinese_words = re.findall(r"[\u4e00-\u9fff]{2,4}", text)

    # Count word frequencies
    word_counts = Counter(chinese_words)

    # Filter stop words
    filtered_words = {
        word: count for word, count in word_counts.items()
        if word not in STOP_WORDS and count >= 2
    }

    # High frequency words
    high_freq = [
        word for word, count in
        sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:top_n]
    ]

    # Action words found in text
    actions = [word for word in ACTION_WORDS if word in text][:top_n]

    # Emotion words found in text
    emotions = [word for word in EMOTION_WORDS if word in text][:top_n]

    # Product/core terms: words >= 3 chars that appear at least once
    product_candidates = [
        word for word, count in word_counts.items()
        if len(word) >= 3 and word not in STOP_WORDS
    ]
    products = product_candidates[:top_n]

    return {
        "highFreq": high_freq,
        "actions": actions,
        "emotions": emotions,
        "products": products,
    }


def truncate_text(text: str, max_length: int = 3000) -> str:
    """Truncate text to a maximum length, adding ellipsis if truncated."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def count_words(text: str) -> int:
    """Count words in text (Chinese characters + English words)."""
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    english_words = len(re.findall(r"[a-zA-Z]+", text))
    return chinese_chars + english_words
