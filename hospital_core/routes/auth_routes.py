from flask import Blueprint, session, jsonify, request, flash, redirect, url_for, render_template
import requests
import urllib3
from flask import current_app
from flask_jwt_extended import set_access_cookies
import json

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("email")
        password = request.form.get("password")

        login_data = {
            "identifier": identifier,
            "password": password
        }

        try:
            response = requests.post(
                f"{current_app.config['ZTN_IAM_URL']}/login",
                json=login_data,
                headers={
                    "X-API-KEY": current_app.config['API_KEY'],
                    "Content-Type": "application/json"
                },
                verify=False
            )

            data = response.json()

            if response.status_code == 200 and data.get("access_token"):
                session["access_token"] = data["access_token"]
                session["role"] = data.get("role")
                session["user_id"] = data.get("user_id")
                session["trust_score"] = data.get("trust_score") 

                # Store MFA flags in session
                session["require_totp"] = data.get("require_totp", False)
                session["require_webauthn"] = data.get("require_webauthn", False)
                session["skip_all_mfa"] = data.get("skip_all_mfa", False)
                session["require_totp_setup"] = data.get("require_totp_setup", False)

                # MFA flows
                if session.get("skip_all_mfa"):
                    pass
                elif session.get("require_totp_setup"):
                    return redirect(url_for("auth.setup_totp_page"))
                elif session.get("require_totp") and not session.get("totp_verified"):
                    return redirect(url_for("auth.verify_totp"))
                elif session.get("require_webauthn") and not session.get("webauthn_verified"):
                    return redirect(url_for("auth.verify_webauthn_page"))

                # Role-based dashboard
                role = data.get("role")
                if role == "admin":
                    return redirect(url_for("dashboard.admin_dashboard"))
                elif role == "doctor":
                    return redirect(url_for("dashboard.doctor_dashboard"))
                elif role == "nurse":
                    return redirect(url_for("dashboard.nurse_dashboard"))
                else:
                    flash("Unknown role.", "danger")
                    return redirect(url_for("auth.login"))
            else:
                flash(data.get("error", "Login failed."), "danger")
                return redirect(url_for("auth.login"))

        except Exception as e:
            print("❌ Login Exception:", e)
            flash("Login error.", "danger")
            return redirect(url_for("auth.login"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# TOTP Section
@auth_bp.route("/setup-totp-page", methods=["GET"])
def setup_totp_page():
    return render_template("auth/setup_totp.html")

@auth_bp.route("/setup-totp", methods=["GET"])
def setup_totp():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Not logged in"}), 401

    try:
        res = requests.get(
            f"{current_app.config['ZTN_IAM_URL']}/enroll-totp",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": current_app.config["API_KEY"]
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("❌ enroll_totp_proxy error:", e)
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/setup-totp/confirm", methods=["POST"])
def confirm_totp_proxy():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Not logged in"}), 401

    try:
        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/setup-totp/confirm",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": current_app.config["API_KEY"]
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("❌ confirm_totp_proxy error:", e)
        return jsonify({"error": str(e)}), 500

# TOTP Section
@auth_bp.route("/verify-totp", methods=["GET"])
def verify_totp():
    return render_template("auth/verify_totp.html")

from flask import make_response  # required for setting cookie
@auth_bp.route("/verify-totp", methods=["POST"])
def verify_totp_post():
    token = request.form.get("totp")
    access_token = session.get("access_token")

    if not access_token:
        flash("Session expired. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    try:
        response = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/verify-totp-login",
            json={"totp": token},
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": current_app.config["API_KEY"]
            },
            verify=False
        )

        data = response.json()

        if response.status_code == 200:
            session["totp_verified"] = True
            session["user_id"] = data.get("user_id")

            # Use session instead of IAM's response
            if session.get("require_webauthn"):
                if data.get("has_webauthn_credentials"):
                    resp = make_response(redirect(url_for("auth.verify_webauthn_page")))
                    resp.set_cookie(
                        "access_token_cookie",
                        access_token,
                        httponly=True,
                        samesite="Lax",
                        secure=False
                    )
                    return resp
                else:
                    return redirect(url_for("auth.setup_webauthn"))

            # No WebAuthn required → role-based dashboard
            role = session.get("role")
            if role == "admin":
                return redirect(url_for("dashboard.admin_dashboard"))
            elif role == "doctor":
                return redirect(url_for("dashboard.doctor_dashboard"))
            elif role == "nurse":
                return redirect(url_for("dashboard.nurse_dashboard"))
            else:
                return redirect(url_for("dashboard.home"))

        flash(data.get("error", "Invalid TOTP code."), "danger")
        return redirect(url_for("auth.verify_totp"))

    except Exception as e:
        print("❌ verify_totp_post error:", e)
        flash("Error verifying TOTP. Try again.", "danger")
        return redirect(url_for("auth.verify_totp"))


@auth_bp.route("/reset-totp", methods=["GET"])
def reset_totp():
    token = request.args.get("token")
    if not token:
        flash("Invalid or expired TOTP reset link.", "danger")
        return redirect(url_for("auth.request_totp_reset"))
    return render_template("auth/verify_totp_reset.html", token=token)

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
            f"{current_app.config['ZTN_IAM_URL']}/request-totp-reset",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json={
                "identifier": identifier,
                "redirect_url": "https://localhost.localdomain:5000/auth/reset-totp"
            },
            verify=False
        )

        # Store IAM reset session cookies
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(response.json()), response.status_code

    except Exception as e:
        print("❌ request_totp_reset error:", e)
        return jsonify({"error": f"Exception occurred: {str(e)}"}), 500


@auth_bp.route("/verify-fallback-totp", methods=["POST"])
def verify_fallback_totp():
    data = request.get_json()

    try:
        session_obj = requests.Session()

        # Forward IAM session cookies
        if "iam_reset_cookies" in session:
            session_obj.cookies = requests.utils.cookiejar_from_dict(session["iam_reset_cookies"])

        response = session_obj.post(
            f"{current_app.config['ZTN_IAM_URL']}/verify-totp-reset",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json=data,
            verify=False
        )

        # Save back updated IAM session cookies
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(response.json()), response.status_code

    except Exception as e:
        print("❌ verify_fallback_totp error:", e)
        return jsonify({"error": f"Exception occurred: {str(e)}"}), 500

# WebAutn Section
@auth_bp.route("/setup-webauthn")
def setup_webauthn():
    if not session.get("totp_verified"):
        flash("Please verify TOTP first.", "warning")
        return redirect(url_for("auth.verify_totp"))

    access_token = session.get("access_token")
    if not access_token:
        flash("Login session expired. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("auth/setup_webauthn.html", access_token=access_token)

@auth_bp.route("/begin-webauthn-registration", methods=["POST"])
def begin_webauthn_registration():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Missing access token"}), 401

    try:
        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/webauthn/register-begin",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json={},  # per spec
            verify=False
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("❌ begin_webauthn_registration error:", e)
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/complete-webauthn-registration", methods=["POST"])
def complete_webauthn_registration():
    access_token = session.get("access_token")
    if not access_token:
        return jsonify({"error": "Missing access token"}), 401

    try:
        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/webauthn/register-complete",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json=request.get_json(),
            verify=False
        )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        print("❌ complete_webauthn_registration error:", e)
        return jsonify({"error": str(e)}), 500

# Render the webauthn page for verification
@auth_bp.route("/verify-webauthn")
def verify_webauthn_page():
    if not session.get("access_token"):
        flash("Login session expired. Please log in again.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("auth/verify_webauthn.html")

@auth_bp.route("/begin-webauthn-verification", methods=["POST"])
def begin_webauthn_verification():
    access_token = session.get("access_token")

    if not access_token:
        return jsonify({"error": "Missing access token"}), 401

    try:
        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/webauthn/assertion-begin",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": current_app.config["API_KEY"]
            },
            verify=False
        )
        result = res.json()

        # Store verification state + user_id for follow-up
        if res.status_code == 200 and "state" in result:
            session["webauthn_assertion_state"] = result["state"]
            session["assertion_user_id"] = result["user_id"]

        return jsonify(result), res.status_code
    except Exception as e:
        print("❌ begin_webauthn_verification error:", e)
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
            f"{current_app.config['ZTN_IAM_URL']}/webauthn/assertion-complete",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-API-KEY": current_app.config["API_KEY"]
            },
            verify=False
        )

        result = res.json()

        if res.status_code == 200 and result.get("access_token"):
            session["access_token"] = result["access_token"]
            session.pop("webauthn_assertion_state", None)
            session.pop("assertion_user_id", None)

            # Set JWT as cookie (crucial fix)
            resp = jsonify(result)
            set_access_cookies(resp, result["access_token"])
            return resp, 200

        return jsonify(result), res.status_code

    except Exception as e:
        print("❌ complete_webauthn_verification error:", e)
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/reset-webauthn-begin", methods=["POST"])
def reset_webauthn_begin():
    data = request.get_json()
    token = data.get("token")

    try:
        session_obj = requests.Session()
        res = session_obj.post(
            f"{current_app.config['ZTN_IAM_URL']}/webauthn/reset-assertion-begin",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json={"token": token},
            verify=False
        )

        # Save IAM session cookies for next step
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ reset_webauthn_begin error:", e)
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/reset-webauthn-complete", methods=["POST"])
def reset_webauthn_complete():
    data = request.get_json()
    try:
        session_obj = requests.Session()

        # Restore cookies from /begin step
        if "iam_reset_cookies" in session:
            session_obj.cookies = requests.utils.cookiejar_from_dict(session["iam_reset_cookies"])

        # Forward to IAM
        res = session_obj.post(
            f"{current_app.config['ZTN_IAM_URL']}/webauthn/reset-assertion-complete",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json=data,
            verify=False
        )

        # Save any updated IAM cookies
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ reset_webauthn_complete error:", e)
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
            f"{current_app.config['ZTN_IAM_URL']}/forgot-password",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json={
                "identifier": identifier,
                "redirect_url": "https://localhost.localdomain:5000/auth/reset-password"
            },
            verify=False
        )

        if response.status_code == 200:
            flash("✔️ Reset link sent. Please check your email.", "success")
            return redirect(url_for("auth.login"))
        else:
            error = response.json().get("error", "Reset request failed.")
            flash(f"❌ {error}", "danger")
            return redirect(url_for("auth.forgot_password"))

    except Exception as e:
        print("❌ forgot_password error:", e)
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

    # POST: handle JSON-based password reset
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

        # Reuse IAM cookies if available
        if "iam_reset_cookies" in session:
            session_obj.cookies = requests.utils.cookiejar_from_dict(session["iam_reset_cookies"])

        response = session_obj.post(
            f"{current_app.config['ZTN_IAM_URL']}/reset-password",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json={
                "token": token,
                "new_password": new_password,
                "confirm_password": confirm_password
            },
            verify=False
        )

        # Update session cookies
        session["iam_reset_cookies"] = requests.utils.dict_from_cookiejar(session_obj.cookies)

        if response.status_code == 202:
            return jsonify(response.json()), 202
        elif response.status_code == 200:
            return jsonify({
                "message": "Your password has been successfully reset. You may now log in with your new credentials."
            }), 200
        else:
            return jsonify({"error": response.json().get("error", "Password reset failed.")}), response.status_code

    except Exception as e:
        print("❌ reset_password error:", e)
        return jsonify({"error": f"Exception occurred: {str(e)}"}), 500


@auth_bp.route("/request-webauthn-reset", methods=["GET", "POST"])
def request_webauthn_reset():
    if request.method == "GET":
        return render_template("auth/request_webauthn_reset.html")

    # POST: initiate external WebAuthn reset
    data = request.get_json()
    identifier = data.get("identifier")

    if not identifier:
        return jsonify({"error": "Email or phone number is required."}), 400

    try:
        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/out-request-webauthn-reset",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json={
                "identifier": identifier,
                "redirect_url": "https://localhost.localdomain:5000/auth/verify-webauthn-reset"
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ request_webauthn_reset error:", e)
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/verify-webauthn-reset", methods=["GET"])
def verify_webauthn_reset_page():
    token = request.args.get("token")
    if not token:
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("auth/verify_webauthn_reset.html", token=token)


@auth_bp.route("/verify-webauthn-reset", methods=["POST"])
def verify_webauthn_reset_action():
    data = request.get_json()
    token = data.get("token")
    password = data.get("password")
    totp = data.get("totp")

    if not token or not password or not totp:
        return jsonify({"error": "All fields are required."}), 400

    try:
        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/out-verify-webauthn-reset/{token}",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json={"password": password, "totp": totp},
            verify=False
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ verify_webauthn_reset_action error:", e)
        return jsonify({"error": str(e)}), 500

# User Management
# Get all users under this tenant
@auth_bp.route("/tenant-users", methods=["GET"])
def get_tenant_users():
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        session_obj = requests.Session()
        res = session_obj.get(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/users",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ get_tenant_users error:", e)
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/tenant-roles", methods=["POST"])
def create_tenant_role():
    try:
        data = request.get_json()
        access_token_cookie = request.cookies.get("access_token_cookie")

        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        session_obj = requests.Session()
        res = session_obj.post(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/roles",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            json=data,
            verify=False
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ create_tenant_role error:", e)
        return jsonify({"error": str(e)}), 500

# Get tenant roles
@auth_bp.route("/tenant-roles", methods=["GET"])
def get_tenant_roles():
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        session_obj = requests.Session()
        res = session_obj.get(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/roles",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            verify=False
        )

        iam_response = res.json()
        return jsonify({"roles": iam_response}), res.status_code

    except Exception as e:
        print("❌ get_tenant_roles error:", e)
        return jsonify({"error": str(e)}), 500


# Register a new tenant user
@auth_bp.route("/tenant-users", methods=["POST"])
def register_tenant_user():
    try:
        data = request.get_json()
        access_token_cookie = request.cookies.get("access_token_cookie")

        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        session_obj = requests.Session()
        res = session_obj.post(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/users",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            json=data,
            verify=False
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ register_tenant_user error:", e)
        return jsonify({"error": str(e)}), 500

# Edit a tenant user
@auth_bp.route("/tenant-users/<int:user_id>", methods=["PUT"])
def update_tenant_user(user_id):
    try:
        data = request.get_json()
        access_token_cookie = request.cookies.get("access_token_cookie")

        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        session_obj = requests.Session()
        res = session_obj.put(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/users/{user_id}",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            json=data,
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ update_tenant_user error:", e)
        return jsonify({"error": str(e)}), 500

# ❌ Delete a tenant user
@auth_bp.route("/tenant-users/<int:user_id>", methods=["DELETE"])
def delete_tenant_user(user_id):
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        session_obj = requests.Session()
        res = session_obj.delete(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/users/{user_id}",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ delete_tenant_user error:", e)
        return jsonify({"error": str(e)}), 500


# Get single tenant user
@auth_bp.route("/tenant-users/<int:user_id>", methods=["GET"])
def get_single_tenant_user(user_id):
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        session_obj = requests.Session()
        res = session_obj.get(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/users/{user_id}",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ get_single_tenant_user error:", e)
        return jsonify({"error": str(e)}), 500


# Settings Section
@auth_bp.route("/tenant-settings-page")
def tenant_settings():
    return render_template("admin/tenant_settings.html")

@auth_bp.route("/tenant-settings", methods=["GET"])
def proxy_get_tenant_settings():
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        res = requests.get(
            f"{current_app.config['ZTN_IAM_URL']}/tenant-settings",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ proxy_get_tenant_settings error:", e)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@auth_bp.route("/change-plan", methods=["POST"])
def proxy_change_plan():
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        data = request.get_json(force=True)

        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/change-plan",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}",
                "Content-Type": "application/json"
            },
            json=data,
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ proxy_change_plan error:", e)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

# System Metrics
@auth_bp.route("/system-metrics", methods=["GET"])
def proxy_system_metrics():
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        res = requests.get(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/system-metrics",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}"
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ proxy_system_metrics error:", e)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

@auth_bp.route("/trust-policy", methods=["GET"])
def get_trust_policy():
    try:
        access_token = request.cookies.get("access_token_cookie")
        if not access_token:
            return jsonify({"error": "Missing access token cookie"}), 401

        res = requests.get(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/trust-policy",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token}",
                "Content-Type": "application/json"
            },
            verify=False
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ get_trust_policy error:", e)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@auth_bp.route("/trust-policy/upload", methods=["POST"])
def upload_trust_policy():
    try:
        access_token = request.cookies.get("access_token_cookie")
        if not access_token:
            return jsonify({"error": "Missing access token cookie"}), 401

        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/trust-policy/upload",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token}"
            },
            files={
                "file": (file.filename, file.stream, file.content_type)
            },
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ upload_trust_policy error:", e)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500

# Real time edit of the uploaded policy:
@auth_bp.route("/trust-policy/edit", methods=["PUT"])
def edit_trust_policy():
    try:
        access_token = request.cookies.get("access_token_cookie")
        if not access_token:
            return jsonify({"error": "Missing access token cookie"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON payload"}), 400

        res = requests.put(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/trust-policy/edit",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token}",
                "Content-Type": "application/json"
            },
            data=json.dumps(data),
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ edit_trust_policy error:", e)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@auth_bp.route("/trust-policy/clear", methods=["DELETE"])
def proxy_clear_trust_policy():
    try:
        access_token_cookie = request.cookies.get("access_token_cookie")
        if not access_token_cookie:
            return jsonify({"error": "Missing access token cookie"}), 401

        res = requests.delete(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/trust-policy/clear",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Cookie": f"access_token_cookie={access_token_cookie}"
            },
            verify=False
        )

        return jsonify(res.json()), res.status_code

    except Exception as e:
        print("❌ proxy_clear_trust_policy error:", e)
        return jsonify({"error": str(e)}), 500


# Refreshing token:
@auth_bp.route("/refresh", methods=["POST"])
def hospital_token_refresh():
    refresh_token_cookie = request.cookies.get("refresh_token_cookie")

    if not refresh_token_cookie:
        return jsonify({"error": "Missing refresh token"}), 401

    try:
        res = requests.post(
            f"{current_app.config['ZTN_IAM_URL']}/refresh",
            cookies={"refresh_token_cookie": refresh_token_cookie},
            headers={"X-API-KEY": current_app.config["API_KEY"]},
            verify=False
        )

        if res.status_code == 200:
            new_access_token = res.json().get("access_token")
            resp = jsonify({"msg": "refreshed"})
            set_access_cookies(resp, new_access_token)
            return resp

        return jsonify({"error": "Token refresh failed"}), 401

    except Exception as e:
        print("❌ Token refresh error:", e)
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# User Profile
@auth_bp.route("/profile", methods=["GET", "POST"])
def user_profile():
    return render_template("dashboard/profile.html")

# Update mfa preference per user
@auth_bp.route("/update-mfa-preference", methods=["PUT"])
def update_mfa_preference():
    access_token_cookie = request.cookies.get("access_token_cookie")
    if not access_token_cookie:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    res = requests.put(
        f"{current_app.config['ZTN_IAM_URL']}/tenant/user/preferred-mfa",
        headers={
            "X-API-KEY": current_app.config["API_KEY"],
            "Cookie": f"access_token_cookie={access_token_cookie}",
            "Content-Type": "application/json"
        },
        json=data,
        verify=False
    )

    return jsonify(res.json()), res.status_code

# Admin enforces the mfa policy for all the tenant users
@auth_bp.route("/enforce-mfa-policy", methods=["GET", "PUT"])
def enforce_mfa_policy():
    access_token_cookie = request.cookies.get("access_token_cookie")
    if not access_token_cookie:
        return jsonify({"error": "Unauthorized"}), 401

    session_obj = requests.Session()
    session_obj.cookies.set("access_token_cookie", access_token_cookie)

    if request.method == "GET":
        res = session_obj.get(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/mfa-policy",
            headers={"X-API-KEY": current_app.config["API_KEY"]},
            verify=False
        )
        return jsonify(res.json()), res.status_code

    if request.method == "PUT":
        data = request.get_json()
        res = session_obj.put(
            f"{current_app.config['ZTN_IAM_URL']}/tenant/mfa-policy",
            headers={
                "X-API-KEY": current_app.config["API_KEY"],
                "Content-Type": "application/json"
            },
            json=data,
            verify=False
        )
        return jsonify(res.json()), res.status_code

@auth_bp.route("/trust-info")
def trust_info():
    return render_template("auth/trust_info.html")
