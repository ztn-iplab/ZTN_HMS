# routes/auth.py or main.py inside hospital app
from flask import Blueprint, session, jsonify, request, flash, redirect, url_for, render_template
import requests

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/setup-totp", methods=["GET"])
def proxy_enroll_totp():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Not logged in"}), 401

    try:
        resp = requests.get(
            "https://localhost.localdomain/api/v1/auth/enroll-totp",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": "mohealthapikey987654"
            },
            verify=False
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/setup-totp/confirm", methods=["POST"])
def proxy_confirm_totp():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Not logged in"}), 401

    try:
        resp = requests.post(
            "https://localhost.localdomain/api/v1/auth/setup-totp/confirm",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": "mohealthapikey987654"
            },
            verify=False
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Verify TOTP
@auth_bp.route("/verify-totp", methods=["POST"])
def verify_totp():
    token = request.form.get("totp")
    access_token = session.get("access_token")
    
    if not access_token:
        flash("Session expired. Please log in again.", "danger")
        return redirect(url_for("login"))

    try:
        response = requests.post(
            "https://localhost.localdomain/api/v1/auth/verify-totp-login",
            json={"totp": token},
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": "mohealthapikey987654"
            },
            verify=False
        )

        print("🔎 ZTN-IAM Status:", response.status_code)
        print("📦 ZTN-IAM Raw Response:", response.text)

        data = response.json()

        if response.status_code == 200:
            session["totp_verified"] = True
            session["user_id"] = data.get("user_id")  # store user_id for WebAuthn routes

            # 🔐 Handle WebAuthn MFA flow
            if data.get("require_webauthn"):
                if data.get("has_webauthn_credentials"):
                    return redirect(url_for("auth.verify_webauthn"))
                else:
                    return redirect(url_for("auth.setup_webauthn"))

            # ✅ Proceed to dashboard if no WebAuthn required
            role = session.get("role")
            if role == "admin":
                return redirect(url_for("admin_dashboard"))
            elif role == "doctor":
                return redirect(url_for("doctor_dashboard"))
            elif role == "nurse":
                return redirect(url_for("nurse_dashboard"))
            else:
                return redirect(url_for("index"))
        else:
            flash(data.get("error", "Invalid TOTP code."), "danger")
            return redirect(url_for("verify_totp"))

    except Exception as e:
        print("❌ TOTP Verify Exception:", e)
        flash("Error verifying TOTP. Try again.", "danger")
        return redirect(url_for("verify_totp"))



# Render the webauthn page for verification

@auth_bp.route("/verify-webauthn")
def verify_webauthn_page():
    return render_template("auth/verify_webauthn.html")


# Verify the Webauthn

# @auth_bp.route("/start-webauthn", methods=["POST"])
# def start_webauthn():
#     access_token = session.get("access_token")
#     if not access_token:
#         return jsonify({"error": "Not logged in"}), 401

#     try:
#         res = requests.post(
#             "https://localhost.localdomain/api/v1/auth/webauthn/assertion-begin",
#             headers={
#                 "Authorization": f"Bearer {access_token}",
#                 "X-API-KEY": "mohealthapikey987654"
#             },
#             verify=False
#         )
#         return jsonify(res.json()), res.status_code
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


@auth_bp.route("/verify-webauthn", methods=["POST"])
def verify_webauthn():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Not logged in"}), 401

    try:
        res = requests.post(
            "https://localhost.localdomain/api/v1/auth/webauthn/assertion-complete",
            json=request.get_json(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": "mohealthapikey987654"
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/setup-webauthn")
def setup_webauthn():
    if not session.get("totp_verified"):
        flash("Please verify TOTP first.", "warning")
        return redirect(url_for("verify_totp"))
    return render_template("auth/setup_webauthn.html")

@auth_bp.route("/auth/begin-webauthn-registration")
def begin_webauthn_registration():
    access_token = session.get("access_token")
    res = requests.post(
        "https://localhost.localdomain/api/v1/auth/webauthn/register-begin",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-API-KEY": "mohealthapikey987654"
        },
        verify=False
    )
    return jsonify(res.json()), res.status_code

@auth_bp.route("/auth/complete-webauthn-registration", methods=["POST"])
def complete_webauthn_registration():
    access_token = session.get("access_token")
    res = requests.post(
        "https://localhost.localdomain/api/v1/auth/webauthn/register-complete",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-API-KEY": "mohealthapikey987654",
            "Content-Type": "application/json"
        },
        json=request.get_json(),
        verify=False
    )
    return jsonify(res.json()), res.status_code
