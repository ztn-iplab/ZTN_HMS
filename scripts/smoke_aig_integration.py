#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import uuid

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from hospital_core import create_app


def post_json(url: str, api_key: str, payload: dict) -> dict:
    resp = requests.post(
        url,
        json=payload,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        verify=False,
        timeout=8,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return {"status_code": resp.status_code, "data": data}


def get_json(url: str, api_key: str, params: dict | None = None) -> dict:
    resp = requests.get(
        url,
        params=params,
        headers={"X-API-Key": api_key},
        verify=False,
        timeout=8,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    return {"status_code": resp.status_code, "data": data}


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test HMS -> ZT-IAM AIg integration")
    parser.add_argument("--iam-base", default="https://localhost/api/v1")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--role", default="doctor")
    parser.add_argument("--trust-score", type=float, default=0.7)
    parser.add_argument("--threshold", type=float, default=0.65)
    args = parser.parse_args()

    iam_base = args.iam_base.rstrip("/")
    corr = f"hms-smoke-{uuid.uuid4().hex[:10]}"
    browser_session = f"browser-{uuid.uuid4().hex[:8]}"

    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="hms-aig-smoke-secret",
        JWT_SECRET_KEY="hms-aig-smoke-jwt-secret",
        ZTN_IAM_URL=iam_base,
        API_KEY=args.api_key,
        # Optional explicit AIg endpoints (derive automatically if omitted)
        ZTN_AIG_OBSERVATIONS_BATCH_URL=f"{iam_base}/aig/observations/batch",
        ZTN_AIG_AUTHORIZE_URL=f"{iam_base}/aig/authorize",
    )

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = args.user_id
            sess["role"] = args.role
            sess["trust_score"] = args.trust_score
            sess["access_token"] = "smoke-token"
            sess["aig_session_id"] = corr

        telemetry_payload = {
            "batch": [
                {
                    "timestamp": None,
                    "session_id": browser_session,
                    "session_label": "smoke-doctor",
                    "page": "/patients/view",
                    "title": "Patients",
                    "event_type": "page_view",
                    "load_ms": 320,
                    "scroll_depth": 0,
                },
                {
                    "timestamp": None,
                    "session_id": browser_session,
                    "session_label": "smoke-doctor",
                    "page": "/patients/view",
                    "title": "Patients",
                    "event_type": "click",
                    "element_tag": "button",
                    "element_id": "open-patient-42",
                    "x": 412,
                    "y": 288,
                },
                {
                    "timestamp": None,
                    "session_id": browser_session,
                    "session_label": "smoke-doctor",
                    "page": "/patients/view",
                    "title": "Patients",
                    "event_type": "scroll",
                    "scroll_depth": 62,
                },
            ]
        }

        hms_resp = client.post("/auth/telemetry", json=telemetry_payload)
        print("HMS /auth/telemetry:", hms_resp.status_code, hms_resp.get_json())

        time.sleep(1.0)

        obs_check = get_json(
            f"{iam_base}/aig/observations",
            args.api_key,
            params={"correlation_id": corr, "limit": 20},
        )
        print("AIg observations query:", obs_check["status_code"])
        print(json.dumps(obs_check["data"], indent=2))

        authz_payload = {
            "action_name": "view_patient_record",
            "action_class": "ehr_read",
            "resource_type": "patient",
            "resource_id": "42",
            "user_id": args.user_id,
            "session_id": corr,
            "correlation_id": corr,
            "threshold": args.threshold,
            "alpha": 0.7,
            "decay_lambda": 0.001,
            "window_seconds": 3600,
            "on_below_threshold": "step_up",
            "metadata_json": {"smoke_script": True},
        }
        authz_resp = post_json(f"{iam_base}/aig/authorize", args.api_key, authz_payload)
        print("AIg authorize:", authz_resp["status_code"])
        print(json.dumps(authz_resp["data"], indent=2))

        dec_check = get_json(
            f"{iam_base}/aig/decisions",
            args.api_key,
            params={"correlation_id": corr, "limit": 10},
        )
        print("AIg decisions query:", dec_check["status_code"])
        print(json.dumps(dec_check["data"], indent=2))


if __name__ == "__main__":
    main()
