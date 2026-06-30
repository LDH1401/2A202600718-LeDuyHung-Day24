# NĐ13/2023 Compliance Checklist — MedViet AI Platform

> Cập nhật: 2026-06-30 · Phạm vi: pipeline xử lý hồ sơ bệnh nhân cho AI training.

## A. Data Localization
- [x] Tất cả patient data lưu trên servers đặt tại Việt Nam (VPS/region `vn-hanoi`)
- [x] Backup cũng phải ở trong lãnh thổ VN (S3-compatible bucket đặt tại VN, versioning bật)
- [x] Log việc transfer data ra ngoài nếu có — OPA rule `denied` chặn export
      `data_classification == "restricted"` khi `destination_country != "VN"`
      (xem [policies/opa_policy.rego](policies/opa_policy.rego))

## B. Explicit Consent
- [x] Thu thập consent trước khi dùng data cho AI training (cờ `consent_ai_training` trong hồ sơ)
- [x] Có mechanism để user rút consent (Right to Erasure) — endpoint `DELETE /api/patients/{id}` (chỉ admin)
- [x] Lưu consent record với timestamp (bảng `consent_log`: patient_id, scope, granted_at, revoked_at)

## C. Breach Notification (72h)
- [x] Có incident response plan (runbook IR + on-call rotation)
- [x] Alert tự động khi phát hiện breach (Prometheus alert rules → Alertmanager → email/Slack)
- [x] Quy trình báo cáo đến cơ quan có thẩm quyền (Bộ Công an / A05) trong 72h kể từ khi phát hiện

## D. DPO Appointment
- [x] Đã bổ nhiệm Data Protection Officer
- [x] DPO có thể liên hệ tại: `dpo@medviet.vn` / hotline nội bộ 1900-xxxx

## E. Technical Controls (mapping từ requirements)
| NĐ13 Requirement | Technical Control | Status | Owner |
|-----------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline (Presidio) | ✅ Done | AI Team |
| Access control | RBAC (Casbin) + ABAC (OPA) | ✅ Done | Platform Team |
| Encryption | AES-256-GCM envelope encryption at rest (SimpleVault), TLS 1.3 in transit | ✅ Done | Infra Team |
| Audit logging | API access log middleware → JSON logs → Loki; thao tác delete/read PII ghi kèm user+timestamp | ✅ Done | Platform Team |
| Breach detection | Prometheus anomaly rules (spike số request `/raw`, 403 rate, export volume) → Alertmanager | ✅ Done | Security Team |

## F. Mô tả technical solution cho các control vừa hoàn thiện

**Audit logging.** Middleware FastAPI ghi mỗi request thành log JSON gồm
`timestamp, username, role, method, path, status_code, client_ip`. Riêng các
hành động nhạy cảm (đọc `/api/patients/raw`, `DELETE /api/patients/{id}`) gắn
nhãn `audit=true`. Log đẩy sang Loki, giữ tối thiểu 12 tháng, immutable
(append-only) để phục vụ điều tra sự cố.

**Breach detection.** Prometheus thu thập metric từ API (request count theo
endpoint/role, tỉ lệ 403, kích thước response của endpoint export). Alert rules:
(1) số lần truy cập `/api/patients/raw` vượt ngưỡng giờ; (2) tỉ lệ 403 tăng đột
biến (dò quét quyền); (3) volume export data bất thường. Alert bắn qua
Alertmanager tới email + Slack on-call, kích hoạt quy trình IR ở mục C.

> Stack quan sát: xem [docker-compose.yml](docker-compose.yml) (MLflow + Prometheus + Grafana).
