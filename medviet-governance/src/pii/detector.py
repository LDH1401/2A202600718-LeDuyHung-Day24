# src/pii/detector.py
"""PII detection cho dữ liệu tiếng Việt dùng Microsoft Presidio.

Chiến lược:
- CCCD và số điện thoại VN: dùng PatternRecognizer (regex) -> chính xác ~100%.
- EMAIL_ADDRESS: dùng recognizer built-in của Presidio.
- PERSON (họ tên): ưu tiên spaCy NER tiếng Việt (vi_core_news_lg); nếu model
  không tải được thì fallback sang một custom recognizer regex cho tên VN để
  pipeline vẫn đạt detection rate > 95%.
"""
import spacy
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Các entity mà pipeline cam kết detect
SUPPORTED_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"]

# Model spaCy tiếng Việt mong muốn (theo đề bài)
PREFERRED_SPACY_MODEL = "vi_core_news_lg"


def _build_cccd_recognizer() -> PatternRecognizer:
    """TASK 2.2.1 — CCCD VN gồm đúng 12 chữ số."""
    cccd_pattern = Pattern(
        name="cccd_pattern",
        regex=r"\b\d{12}\b",          # đúng 12 chữ số
        score=0.9,
    )
    return PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[cccd_pattern],
        context=["cccd", "căn cước", "chứng minh", "cmnd"],
        supported_language="vi",
    )


def _build_phone_recognizer() -> PatternRecognizer:
    """TASK 2.2.2 — SĐT VN: 0[3|5|7|8|9] + 8 chữ số."""
    return PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern(
            name="vn_phone",
            regex=r"\b0[35789]\d{8}\b",
            score=0.85,
        )],
        context=["điện thoại", "sdt", "phone", "liên hệ"],
        supported_language="vi",
    )


def _build_vn_name_recognizer() -> PatternRecognizer:
    """Custom recognizer cho họ tên tiếng Việt (entity PERSON).

    Bắt chuỗi 2-4 từ viết hoa chữ cái đầu, hỗ trợ đầy đủ dấu tiếng Việt.
    Dùng làm lớp dự phòng cho spaCy NER (vốn yếu/không có sẵn cho tiếng Việt).
    """
    # [A-ZÀ-Ỹ] phủ chữ hoa Latin + toàn bộ chữ hoa có dấu VN (gồm Đ);
    # [a-zà-ỹ] phủ chữ thường tương ứng (gồm đ).
    name_regex = r"\b[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,3}\b"
    return PatternRecognizer(
        supported_entity="PERSON",
        patterns=[Pattern(name="vn_person", regex=name_regex, score=0.6)],
        context=["bệnh nhân", "họ tên", "bác sĩ", "tên"],
        supported_language="vi",
    )


def _build_nlp_engine():
    """Tạo NLP engine spaCy. TASK 2.2.3.

    Thử model tiếng Việt mong muốn; nếu chưa cài thì tạo pipeline blank "vi"
    (không NER) để Presidio vẫn khởi tạo được — phần PERSON khi đó dựa vào
    custom recognizer regex ở trên.
    """
    model_name = PREFERRED_SPACY_MODEL
    if not spacy.util.is_package(PREFERRED_SPACY_MODEL):
        # Fallback: tạo & lưu một pipeline blank vi để spaCy.load được
        import tempfile
        import os
        blank_dir = os.path.join(tempfile.gettempdir(), "vi_blank_spacy")
        if not os.path.exists(blank_dir):
            spacy.blank("vi").to_disk(blank_dir)
        model_name = blank_dir

    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "vi", "model_name": model_name}],
    })
    return provider.create_engine()


def build_vietnamese_analyzer() -> AnalyzerEngine:
    """Xây dựng AnalyzerEngine với các recognizer tùy chỉnh cho VN. TASK 2.2.4."""
    nlp_engine = _build_nlp_engine()

    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=["vi"],
    )

    # Add các recognizer tùy chỉnh
    analyzer.registry.add_recognizer(_build_cccd_recognizer())
    analyzer.registry.add_recognizer(_build_phone_recognizer())
    analyzer.registry.add_recognizer(_build_vn_name_recognizer())

    return analyzer


def detect_pii(text: str, analyzer: AnalyzerEngine) -> list:
    """Detect PII trong text tiếng Việt.

    Trả về list các RecognizerResult cho các entity:
    PERSON, EMAIL_ADDRESS, VN_CCCD, VN_PHONE.
    """
    if text is None or str(text).strip() == "":
        return []
    results = analyzer.analyze(
        text=str(text),
        language="vi",
        entities=SUPPORTED_ENTITIES,
    )
    return results
