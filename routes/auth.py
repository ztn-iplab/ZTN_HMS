# routes/auth.py or main.py inside hospital app
from flask import Blueprint, session, jsonify, request, flash, redirect, url_for, render_template
import requests

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

ZTN_IAM_URL = "https://localhost.localdomain/api/v1/auth"
API_KEY = "mohealthapikey987654"

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
from flask import make_response

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

        data = response.json()

        if response.status_code == 200:
            session["totp_verified"] = True
            session["user_id"] = data.get("user_id")

            # 🌐 Handle WebAuthn MFA flow
            if data.get("require_webauthn"):
                if data.get("has_webauthn_credentials"):
                    resp = make_response(redirect(url_for("auth.verify_webauthn_page")))
                    resp.set_cookie("access_token_cookie", access_token, httponly=True, samesite="Lax", secure=False)
                    return resp
                else:
                    return redirect(url_for("auth.setup_webauthn"))

            # ✅ No WebAuthn — proceed to dashboard
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



@auth_bp.route("/setup-webauthn")
def setup_webauthn():
    if not session.get("totp_verified"):
        flash("Please verify TOTP first.", "warning")
        return redirect(url_for("verify_totp"))

    access_token = session.get("access_token")
    if not access_token:
        flash("Login session expired. Please log in again.", "danger")
        return redirect(url_for("login"))

    return render_template("auth/setup_webauthn.html", access_token=access_token)


@auth_bp.route("/begin-webauthn-registration", methods=["POST"])
def begin_webauthn_registration():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Missing access token"}), 401

    try:
        res = requests.post(
            "https://localhost.localdomain/api/v1/auth/webauthn/register-begin",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": "mohealthapikey987654",
                "Content-Type": "application/json"
            },
            json={},  # WebAuthn registration usually takes an empty POST body
            verify=False
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/complete-webauthn-registration", methods=["POST"])
def complete_webauthn_registration():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Missing access token"}), 401

    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Render the webauthn page for verification

@auth_bp.route("/verify-webauthn")
def verify_webauthn_page():
    if not session.get("access_token"):
        flash("Login session expired. Please log in again.", "danger")
        return redirect(url_for("login"))
    return render_template("auth/verify_webauthn.html")


@auth_bp.route("/begin-webauthn-verification", methods=["POST"])
def begin_webauthn_verification():
    access_token = session.get("access_token")

    if not access_token:
        return jsonify({"error": "Missing access token"}), 401

    try:
        res = requests.post(
            "https://localhost.localdomain/api/v1/auth/webauthn/assertion-begin",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": "mohealthapikey987654"
            },
            verify=False
        )
        result = res.json()

        # 🧠 Extract state and user_id into local session
        if res.status_code == 200 and "state" in result:
            session["webauthn_assertion_state"] = result["state"]
            session["assertion_user_id"] = result["user_id"]

        return jsonify(result), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/complete-webauthn-verification", methods=["POST"])
def complete_webauthn_verification():
    access_token = session.get("access_token")
    assertion_state = session.get("webauthn_assertion_state")
    assertion_user_id = session.get("assertion_user_id")

    if not access_token:
        return jsonify({"error": "Missing access token"}), 401
    
    assertion = request.get_json()

    payload = {
        **assertion,
        "state": assertion_state,
        "user_id": assertion_user_id
    }

    try:
        res = requests.post(
            "https://localhost.localdomain/api/v1/auth/webauthn/assertion-complete",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": "mohealthapikey987654"
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500






