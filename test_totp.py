import pyotp

secret = "NKDQY62UDM4SSNQLMJ6ABAGGEXM6VQDL"
totp = pyotp.TOTP(secret)
print("🔐 Current TOTP:", totp.now())

