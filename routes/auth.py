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

        result = res.json()
       
        # ✅ NEW: Save final access token if WebAuthn verification is successful
        if res.status_code == 200 and result.get("access_token"):
            session["access_token"] = result.get("access_token")

            session["access_token"] = result["access_token"]
            session.pop("webauthn_assertion_state", None)
            session.pop("assertion_user_id", None)

        return jsonify(result), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
#          FallBacks
# =========================

@auth_bp.route("/request-totp-reset", methods=["GET", "POST"])
def request_totp_reset():
    if request.method == "GET":
        return render_template("auth/request_totp_reset.html")

    # POST: handle identifier submission from JS
    if request.content_type != "application/json":
        return jsonify({"error": "Unsupported Media Type"}), 415

    data = request.get_json()
    identifier = data.get("identifier")

    if not identifier:
        return jsonify({"error": "Missing identifier."}), 400

    try:
        session_obj = requests.Session()

        # Include IAM session cookies if available
        if "iam_reset_cookies" in session:
            session_obj.cookies = requests.utils.cookiejar_from_dict(session["iam_reset_cookies"])

        response = session_obj.post(
            f"{ZTN_IAM_URL}/request-totp-reset",
            headers={
                "X-API-KEY": API_KEY,
                "Content-Type": "application/json"
            },
            json={"identifier": identifier},
            verify=False
        )

        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(response.json()), response.status_code

    except Exception as e:
        return jsonify({"error": f"Exception occurred: {str(e)}"}), 500


@auth_bp.route("/reset-totp", methods=["GET"])
def reset_totp():
    token = request.args.get("token")
    if not token:
        flash("Invalid or expired TOTP reset link.", "danger")
        return redirect(url_for("auth.request_totp_reset"))
    return render_template("auth/verify_totp_reset.html", token=token)


@auth_bp.route("/verify-fallback-totp", methods=["POST"])
def proxy_verify_fallback_totp():
    data = request.get_json()

    try:
        session_obj = requests.Session()

        # 🛡️ Forward IAM session cookies
        if "iam_reset_cookies" in session:
            session_obj.cookies = requests.utils.cookiejar_from_dict(session["iam_reset_cookies"])

        response = session_obj.post(
            f"{ZTN_IAM_URL}/verify-totp-reset",
            headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
            json=data,
            verify=False
        )

        # 🔁 Update cookies
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(response.json()), response.status_code

    except Exception as e:
        return jsonify({"error": f"Exception occurred: {str(e)}"}), 500



@auth_bp.route("/reset-webauthn-begin", methods=["POST"])
def reset_webauthn_begin():
    data = request.get_json()
    token = data.get("token")
    try:
        session_obj = requests.Session()
        res = session_obj.post(
            f"{ZTN_IAM_URL}/webauthn/reset-assertion-begin",
            headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
            json={"token": token},
            verify=False
        )

        # 🔐 Store IAM session cookies for reuse
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(res.json()), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/reset-webauthn-complete", methods=["POST"])
def reset_webauthn_complete():
    data = request.get_json()
    try:
        session_obj = requests.Session()

        # 🔁 Restore existing cookies from /begin
        if "iam_reset_cookies" in session:
            session_obj.cookies = requests.utils.cookiejar_from_dict(session["iam_reset_cookies"])

        # 🌐 Post to ZTN-IAM
        res = session_obj.post(
            f"{ZTN_IAM_URL}/webauthn/reset-assertion-complete",
            headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
            json=data,
            verify=False
        )

        # ✅ Save updated IAM session cookies (important!)
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(res.json()), res.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("auth/forgot_password.html")

    identifier = request.form.get("identifier")
    if not identifier:
        flash("Please provide your email or mobile number.", "warning")
        return redirect(url_for("auth.forgot_password"))

    try:
        response = requests.post(
            "https://localhost.localdomain/api/v1/auth/forgot-password",
            headers={
                "X-API-KEY": API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "identifier": identifier,
                "redirect_url": "https://localhost.localdomain:5000/auth/reset-password"  #
            },
            verify=False
        )

        if response.status_code == 200:
            flash("✔️ Reset link sent. Please check your email.", "success")
            return redirect(url_for("login"))
        else:
            error = response.json().get("error", "Reset request failed.")
            flash(f"❌ {error}", "danger")
            return redirect(url_for("auth.forgot_password"))

    except Exception as e:
        flash(f"⚠️ Error contacting IAM: {str(e)}", "danger")
        return redirect(url_for("auth.forgot_password"))



@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        token = request.args.get("token")
        if not token:
            flash("Invalid or expired reset link.", "danger")
            return redirect(url_for("auth.forgot_password"))
        return render_template("auth/reset_password.html", token=token)

    # POST: handle password reset from JS
    if request.content_type != "application/json":
        return jsonify({"error": "Unsupported Media Type"}), 415

    data = request.get_json()
    token = data.get("token")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not new_password or not confirm_password or not token:
        return jsonify({"error": "Missing required fields."}), 400

    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    try:
        session_obj = requests.Session()

        # ✅ Reuse IAM session cookies
        if "iam_reset_cookies" in session:
            session_obj.cookies = requests.utils.cookiejar_from_dict(session["iam_reset_cookies"])

        response = session_obj.post(
            f"{ZTN_IAM_URL}/reset-password",
            headers={
                "X-API-KEY": API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "token": token,
                "new_password": new_password,
                "confirm_password": confirm_password
            },
            verify=False
        )

        # 🔁 Refresh cookies in case IAM issues new ones
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        if response.status_code == 202:
            return jsonify(response.json()), 202
        elif response.status_code == 200:
            return jsonify({"message": "Your password has been successfully reset. You may now log in with your new credentials."}), 200
        else:
            return jsonify({"error": response.json().get("error", "Password reset failed.")}), response.status_code

    except Exception as e:
        return jsonify({"error": f"Exception occurred: {str(e)}"}), 500

