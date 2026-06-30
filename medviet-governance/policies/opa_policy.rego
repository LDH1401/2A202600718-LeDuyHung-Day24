package medviet.data_access

import future.keywords.if
import future.keywords.in

# Default: deny all
default allow := false

# Quyết định cuối cùng: cho phép NẾU có rule cấp quyền VÀ không bị deny override.
allow if {
	role_permits
	not denied
}

# ---------------------------------------------------------------------------
# Các rule cấp quyền theo role
# ---------------------------------------------------------------------------

# Admin được phép tất cả
role_permits if {
	input.user.role == "admin"
}

# ML Engineer: đọc/ghi training data và model artifacts
role_permits if {
	input.user.role == "ml_engineer"
	input.resource in {"training_data", "model_artifacts"}
	input.action in {"read", "write"}
}

# Data Analyst: chỉ đọc aggregated metrics và viết reports
role_permits if {
	input.user.role == "data_analyst"
	input.resource == "aggregated_metrics"
	input.action == "read"
}

role_permits if {
	input.user.role == "data_analyst"
	input.resource == "reports"
	input.action == "write"
}

# Intern: chỉ được access sandbox
role_permits if {
	input.user.role == "intern"
	input.resource == "sandbox_data"
	input.action in {"read", "write"}
}

# ---------------------------------------------------------------------------
# Các rule DENY (override mọi allow ở trên)
# ---------------------------------------------------------------------------

# ML Engineer KHÔNG được delete production data
denied if {
	input.user.role == "ml_engineer"
	input.resource == "production_data"
	input.action == "delete"
}

# Không ai được export restricted data ra ngoài VN servers (NĐ13 - localization)
denied if {
	input.data_classification == "restricted"
	input.destination_country != "VN"
}
