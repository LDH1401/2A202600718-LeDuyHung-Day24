# tests/test_pii.py
import pytest
import pandas as pd
from src.pii.anonymizer import MedVietAnonymizer, load_patient_csv


@pytest.fixture(scope="module")
def anonymizer():
    return MedVietAnonymizer()


@pytest.fixture
def sample_df():
    return load_patient_csv("data/raw/patients_raw.csv").head(50)


class TestPIIDetection:

    def test_cccd_detected(self, anonymizer):
        text = "Bệnh nhân Nguyen Van A, CCCD: 012345678901"
        results = anonymizer.analyzer.analyze(text=text, language="vi",
                                              entities=["VN_CCCD"])
        assert len(results) >= 1
        assert text[results[0].start:results[0].end] == "012345678901"

    def test_phone_detected(self, anonymizer):
        text = "Liên hệ: 0912345678"
        results = anonymizer.analyzer.analyze(text=text, language="vi",
                                              entities=["VN_PHONE"])
        assert len(results) >= 1
        assert text[results[0].start:results[0].end] == "0912345678"

    def test_email_detected(self, anonymizer):
        text = "Email: nguyenvana@gmail.com"
        results = anonymizer.analyzer.analyze(text=text, language="vi",
                                              entities=["EMAIL_ADDRESS"])
        assert len(results) >= 1
        assert "nguyenvana@gmail.com" in text[results[0].start:results[0].end]

    # --- TASK QUAN TRỌNG ---
    def test_detection_rate_above_95_percent(self, anonymizer, sample_df):
        """Pipeline phải đạt >95% detection rate."""
        pii_columns = ["ho_ten", "cccd", "so_dien_thoai", "email"]
        rate = anonymizer.calculate_detection_rate(sample_df, pii_columns)
        print(f"\nDetection rate: {rate:.2%}")
        assert rate >= 0.95, f"Detection rate {rate:.2%} < 95%"


class TestAnonymization:

    def test_pii_not_in_output(self, anonymizer, sample_df):
        """Sau anonymization, không còn CCCD gốc trong output."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        output_blob = df_anon.to_csv(index=False)
        for original_cccd in sample_df["cccd"]:
            assert str(original_cccd) not in output_blob

    def test_non_pii_columns_unchanged(self, anonymizer, sample_df):
        """Cột benh và ket_qua_xet_nghiem phải giữ nguyên."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        pd.testing.assert_series_equal(df_anon["benh"], sample_df["benh"])
        pd.testing.assert_series_equal(
            df_anon["ket_qua_xet_nghiem"], sample_df["ket_qua_xet_nghiem"])
        pd.testing.assert_series_equal(
            df_anon["patient_id"], sample_df["patient_id"])
