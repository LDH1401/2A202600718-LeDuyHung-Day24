# src/pii/anonymizer.py
import hashlib

import pandas as pd
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from faker import Faker

from .detector import build_vietnamese_analyzer, detect_pii

fake = Faker("vi_VN")

# Các cột định danh phải đọc dạng chuỗi để KHÔNG mất số 0 đứng đầu
# (vd CCCD "012..." hoặc SĐT "0313...").
ID_COLUMN_DTYPES = {"cccd": str, "so_dien_thoai": str, "patient_id": str}


def load_patient_csv(path: str) -> pd.DataFrame:
    """Đọc CSV bệnh nhân, giữ nguyên cột ID dạng chuỗi."""
    return pd.read_csv(path, dtype=ID_COLUMN_DTYPES)


def _fake_cccd() -> str:
    """Sinh CCCD giả 12 chữ số."""
    return "".join(str(fake.random_digit()) for _ in range(12))


def _fake_phone() -> str:
    """Sinh SĐT VN giả hợp lệ: 0[3|5|7|8|9] + 8 số."""
    prefix = fake.random_element(elements=("3", "5", "7", "8", "9"))
    return "0" + prefix + "".join(str(fake.random_digit()) for _ in range(8))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class MedVietAnonymizer:

    def __init__(self):
        self.analyzer = build_vietnamese_analyzer()
        self.anonymizer = AnonymizerEngine()

    def anonymize_text(self, text: str, strategy: str = "replace") -> str:
        """Anonymize text với strategy được chọn.

        Strategies:
        - "mask"    : che ký tự bằng '*' (giữ lại ký tự đầu)
        - "replace" : thay bằng fake data (dùng Faker)
        - "hash"    : SHA-256 one-way hash
        """
        text = str(text)
        results = detect_pii(text, self.analyzer)
        if not results:
            return text

        if strategy == "replace":
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": fake.email()}),
                "VN_CCCD": OperatorConfig("replace", {"new_value": _fake_cccd()}),
                "VN_PHONE": OperatorConfig("replace", {"new_value": _fake_phone()}),
            }
        elif strategy == "mask":
            # Che toàn bộ trừ ký tự đầu của mỗi entity (from_end=False)
            operators = {
                "DEFAULT": OperatorConfig("mask", {
                    "masking_char": "*",
                    "chars_to_mask": 100,   # che tối đa, presidio tự giới hạn theo độ dài
                    "from_end": False,
                }),
            }
        elif strategy == "hash":
            operators = {
                "DEFAULT": OperatorConfig("hash", {"hash_type": "sha256"}),
            }
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Anonymize toàn bộ DataFrame.

        - ho_ten, dia_chi, email: dùng anonymize_text()
        - cccd, so_dien_thoai: replace trực tiếp bằng fake data
        - benh, ket_qua_xet_nghiem, patient_id: GIỮ NGUYÊN
        """
        df_anon = df.copy()

        text_cols = [c for c in ("ho_ten", "dia_chi", "email", "bac_si_phu_trach")
                     if c in df_anon.columns]
        for col in text_cols:
            df_anon[col] = df_anon[col].astype(str).apply(
                lambda v: self.anonymize_text(v, strategy="replace")
            )

        if "cccd" in df_anon.columns:
            df_anon["cccd"] = [_fake_cccd() for _ in range(len(df_anon))]
        if "so_dien_thoai" in df_anon.columns:
            df_anon["so_dien_thoai"] = [_fake_phone() for _ in range(len(df_anon))]

        # benh, ket_qua_xet_nghiem, patient_id, ngay_sinh, ngay_kham: giữ nguyên
        return df_anon

    def calculate_detection_rate(self,
                                 original_df: pd.DataFrame,
                                 pii_columns: list) -> float:
        """Tính % ô PII được detect thành công (mục tiêu > 95%)."""
        total = 0
        detected = 0

        for col in pii_columns:
            for value in original_df[col].astype(str):
                total += 1
                results = detect_pii(value, self.analyzer)
                if len(results) > 0:
                    detected += 1

        return detected / total if total > 0 else 0.0
