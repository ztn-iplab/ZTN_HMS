from hospital_app import create_app
from flask import request, current_app

app = create_app()

@app.context_processor
def inject_current_endpoint():
    return {"current_endpoint": request.endpoint}

if __name__ == "__main__":
    app.run(debug=True, ssl_context=('certs/hospital_app.crt', 'certs/hospital_app.key'))