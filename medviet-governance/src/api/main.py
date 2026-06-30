# src/api/main.py
import os

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer, load_patient_csv

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

# Đường dẫn dữ liệu tuyệt đối (độc lập với CWD khi chạy uvicorn)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DATA_PATH = os.path.join(_ROOT, "data", "raw", "patients_raw.csv")


# --- ENDPOINT 1 --- chỉ admin
@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(current_user: dict = Depends(get_current_user)):
    """Trả về 10 raw patient records (chỉ admin được phép)."""
    df = load_patient_csv(RAW_DATA_PATH).head(10)
    return JSONResponse(content={
        "requested_by": current_user["username"],
        "count": len(df),
        "records": df.to_dict(orient="records"),
    })


# --- ENDPOINT 2 --- ml_engineer + admin
@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(current_user: dict = Depends(get_current_user)):
    """Trả về anonymized data (ml_engineer và admin được phép)."""
    df = load_patient_csv(RAW_DATA_PATH).head(10)
    df_anon = anonymizer.anonymize_dataframe(df)
    return JSONResponse(content={
        "requested_by": current_user["username"],
        "count": len(df_anon),
        "records": df_anon.to_dict(orient="records"),
    })


# --- ENDPOINT 3 --- data_analyst + ml_engineer + admin
@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(current_user: dict = Depends(get_current_user)):
    """Trả về aggregated metrics (không chứa PII): số bệnh nhân theo loại bệnh."""
    df = load_patient_csv(RAW_DATA_PATH)
    counts = df["benh"].value_counts().to_dict()
    return JSONResponse(content={
        "requested_by": current_user["username"],
        "total_patients": int(len(df)),
        "by_condition": counts,
        "avg_test_result": round(float(df["ket_qua_xet_nghiem"].mean()), 2),
    })


# --- ENDPOINT 4 --- chỉ admin
@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(patient_id: str,
                         current_user: dict = Depends(get_current_user)):
    """Xóa bệnh nhân — chỉ admin; role khác nhận 403 (ở require_permission)."""
    return JSONResponse(content={
        "deleted": patient_id,
        "deleted_by": current_user["username"],
        "status": "ok",
    })


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
