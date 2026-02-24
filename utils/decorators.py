from functools import wraps
import uuid

import requests
import urllib3
from flask import current_app, flash, redirect, request, session, url_for

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("access_token") or session.get("role") != "admin":
            flash("Session expired. Please login again.", "danger")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def _resolve_aig_authorize_url() -> str:
    explicit = (current_app.config.get("ZTN_AIG_AUTHORIZE_URL") or "").strip()
    if explicit:
        return explicit

    base = (current_app.config.get("ZTN_IAM_URL") or "").rstrip("/")
    if not base:
        raise RuntimeError("ZTN_IAM_URL is not configured")

    if base.endswith("/auth"):
        return f"{base[:-5]}/aig/authorize"
    return f"{base}/aig/authorize"


def aig_required(action_name: str, action_class: str | None = None, threshold: float | None = None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not session.get("access_token"):
                flash("Session expired. Please login again.", "danger")
                return redirect(url_for("auth.login"))

            # Stable session correlation for AIg traces across multiple actions.
            aig_session_id = session.get("aig_session_id")
            if not aig_session_id:
                aig_session_id = str(uuid.uuid4())
                session["aig_session_id"] = aig_session_id

            request_trace_id = f"hms-{uuid.uuid4().hex[:12]}"
            exp_run_id = session.get("aig_experiment_run_id")
            exp_actor_label = session.get("aig_actor_label") or "hms_session_actor"
            exp_participant_id = session.get("aig_participant_id")
            payload = {
                "action_name": action_name,
                "action_class": action_class,
                "user_id": session.get("user_id"),
                "session_id": aig_session_id,
                # Keep correlation stable across the HMS session so AIg can accumulate history.
                "correlation_id": aig_session_id,
                "experiment_run_id": exp_run_id,
                "actor_label": exp_actor_label,
                "resource_id": str(kwargs.get("patient_id") or kwargs.get("appointment_id") or ""),
                "metadata_json": {
                    "request_trace_id": request_trace_id,
                    "hms_route": request.path,
                    "method": request.method,
                    "role": session.get("role"),
                    "participant_id": exp_participant_id,
                    "scenario_label": session.get("aig_scenario_label"),
                    "remote_addr": request.headers.get("X-Forwarded-For") or request.remote_addr,
                },
            }
            if threshold is not None:
                payload["threshold"] = threshold

            try:
                res = requests.post(
                    _resolve_aig_authorize_url(),
                    json=payload,
                    headers={
                        "X-API-Key": current_app.config["API_KEY"],
                        "Content-Type": "application/json",
                    },
                    verify=False,
                    timeout=8,
                )
                data = res.json()
            except Exception as exc:
                flash(f"AIg authorization service error: {exc}", "danger")
                return redirect(url_for("auth.login"))

            if res.status_code != 200 or data.get("status") != "ok":
                flash(data.get("detail") or data.get("error") or "AIg authorization failed.", "danger")
                return redirect(url_for("auth.login"))

            session["aig_last_decision"] = {
                "correlation_id": aig_session_id,
                "request_trace_id": request_trace_id,
                "action_name": action_name,
                "experiment_run_id": exp_run_id,
                "decision": data.get("decision"),
                "c_value": data.get("c_value"),
                "threshold": data.get("threshold"),
                "reason": data.get("reason"),
            }

            decision = data.get("decision")
            if decision == "allow":
                return view_func(*args, **kwargs)

            if decision == "step_up":
                flash(
                    "Additional verification is required before this action (AIg continuity check).",
                    "warning",
                )
                return redirect(url_for("auth.verify_totp"))

            flash("Action denied by AIg continuity policy.", "danger")
            return redirect(url_for("dashboard.home"))

        return wrapper

    return decorator
