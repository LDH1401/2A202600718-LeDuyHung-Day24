# src/quality/validation.py
"""Data quality validation cho patient data dùng Great Expectations (API 1.x).

Lưu ý: đề bài viết theo GE 0.17; môi trường này dùng GE >=1.0 nên API đã đổi
(ExpectationSuite + gx.expectations.*). Logic & các expectation giữ nguyên ý đồ.
"""
import re

import pandas as pd
import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite

VALID_CONDITIONS = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
EMAIL_REGEX = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
CRITICAL_COLUMNS = ["patient_id", "benh", "ket_qua_xet_nghiem"]


def build_patient_expectation_suite() -> ExpectationSuite:
    """Tạo expectation suite cho patient data."""
    suite = ExpectationSuite(name="patient_data_suite")

    # 1. patient_id không được null
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="patient_id"))

    # 2. cccd phải có đúng 12 ký tự
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToEqual(column="cccd", value=12))

    # 3. ket_qua_xet_nghiem phải trong khoảng [0, 50]
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="ket_qua_xet_nghiem", min_value=0, max_value=50))

    # 4. benh phải thuộc danh sách hợp lệ
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="benh", value_set=VALID_CONDITIONS))

    # 5. email phải match regex pattern
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="email", regex=EMAIL_REGEX))

    # 6. Không được có duplicate patient_id
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="patient_id"))

    return suite


def run_expectation_suite(df: pd.DataFrame) -> dict:
    """Chạy suite trên DataFrame, trả về kết quả tổng hợp."""
    context = gx.get_context(mode="ephemeral")
    suite = context.suites.add(build_patient_expectation_suite())

    batch_def = (
        context.data_sources.add_pandas("pandas_src")
        .add_dataframe_asset("patients")
        .add_batch_definition_whole_dataframe("batch")
    )
    results = batch_def.get_batch(batch_parameters={"dataframe": df}) \
                       .validate(suite)

    failed = [r["expectation_config"]["type"]
              for r in results["results"] if not r["success"]]
    return {"success": results["success"], "failed_expectations": failed}


def validate_anonymized_data(filepath: str) -> dict:
    """Validate anonymized data. Trả về dict success/failed_checks/stats."""
    # cccd phải đọc dạng chuỗi để giữ độ dài 12 (không mất số 0 đầu)
    df = pd.read_csv(filepath, dtype={"cccd": str, "so_dien_thoai": str,
                                      "patient_id": str})
    results = {
        "success": True,
        "failed_checks": [],
        "stats": {"total_rows": len(df), "columns": list(df.columns)},
    }

    def fail(check: str):
        results["success"] = False
        results["failed_checks"].append(check)

    # Check 1: cccd không còn ở dạng số CCCD thật 12 chữ số thuần
    # (sau anonymization vẫn là 12 chữ số nhưng là fake — ở đây chỉ kiểm tra
    #  định dạng hợp lệ 12 ký tự, không phải giá trị gốc nào đó cụ thể).
    if "cccd" in df.columns:
        bad = df["cccd"].astype(str).apply(lambda x: len(x) != 12 or not x.isdigit())
        if bad.any():
            fail(f"cccd_format_invalid ({int(bad.sum())} rows)")

    # Check 2: Không có null trong các cột quan trọng
    for col in CRITICAL_COLUMNS:
        if col in df.columns and df[col].isnull().any():
            fail(f"null_in_{col}")

    # Check 3: benh thuộc tập hợp lệ
    if "benh" in df.columns:
        invalid = ~df["benh"].isin(VALID_CONDITIONS)
        if invalid.any():
            fail(f"invalid_benh ({int(invalid.sum())} rows)")

    # Check 4: email đúng định dạng
    if "email" in df.columns:
        pattern = re.compile(EMAIL_REGEX)
        bad_email = ~df["email"].astype(str).apply(lambda x: bool(pattern.match(x)))
        if bad_email.any():
            fail(f"invalid_email ({int(bad_email.sum())} rows)")

    # Check 5: patient_id duy nhất
    if "patient_id" in df.columns and df["patient_id"].duplicated().any():
        fail("duplicate_patient_id")

    return results


if __name__ == "__main__":
    import json
    df = pd.read_csv("data/raw/patients_raw.csv",
                     dtype={"cccd": str, "so_dien_thoai": str, "patient_id": str})
    print("GE suite:", json.dumps(run_expectation_suite(df), ensure_ascii=False))
    print("Custom validation:",
          json.dumps(validate_anonymized_data("data/raw/patients_raw.csv"),
                     ensure_ascii=False))
