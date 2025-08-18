# backend/app.py
from __future__ import annotations
import os, math, sqlite3
from typing import Dict, Any
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, g
from joblib import load
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import joblib
from functools import wraps

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(APP_DIR, "model.joblib")
DATABASE_PATH = os.path.join(APP_DIR, "users.db")

app = Flask(
    __name__,
    static_folder=os.path.join(APP_DIR, "static"),
    template_folder=os.path.join(APP_DIR, "templates")
)
app.wsgi_app = ProxyFix(app.wsgi_app)

app.secret_key = "supersecretkey123"

# ------------------- DATABASE HELPER -------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ------------------- MODEL LOADING (Unchanged) -------------------
model = None
model_features = [
    "dog_vaccinated", "dog_type", "dog_behavior", "region_prevalence",
    "bite_location", "bite_severity", "previous_vaccine",
    "time_to_clean_minutes", "age"
]

def load_model():
    global model
    try:
        if not os.path.exists(MODEL_PATH):
            print(f"[WARNING] Model file not found at {MODEL_PATH}.")
            model = None
            return
        model = load(MODEL_PATH)
        print(f"[INFO] Model loaded from {MODEL_PATH}")
    except Exception as e:
        model = None
        print(f"[ERROR] Could not load model: {e}")

load_model()

# ------------------- HELPERS (Unchanged) -------------------
def norm_bool_str(x: str) -> str:
    if x is None: return "Unknown"
    s = str(x).strip().lower()
    if s in ("yes","y","true","1"): return "Yes"
    if s in ("no","n","false","0"): return "No"
    return "Unknown"
def norm_choice(x: str, allowed: Dict[str, str], default_key: str) -> str:
    if x is None: return allowed.get(default_key, default_key)
    s = str(x).strip().lower()
    return allowed.get(s, allowed.get(default_key, default_key))
def coerce_positive_number(x, default=0):
    try:
        v = float(x)
        if math.isnan(v) or v < 0: return default
        return v
    except Exception: return default
def preprocess_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    dog_type_map={"stray":"Stray","pet":"Pet","wild":"Wild"}
    behavior_map={"calm":"Calm","aggressive":"Aggressive","sick":"Sick","playful":"Playful","unusual movements":"Unusual Movements","unusual":"Unusual Movements"}
    region_map={"low":"Low","medium":"Medium","high":"High","unknown":"Unknown"}
    location_map={"leg":"Leg","arm":"Arm","hand":"Hand","finger":"Finger","face":"Face","neck":"Neck","torso":"Torso"}
    severity_map={"scratch":"Scratch","superficial bite":"Superficial bite","deep bite":"Deep bite","multiple deep wounds":"Multiple deep wounds","severe tissue damage":"Severe tissue damage"}
    return {"dog_vaccinated":norm_bool_str(payload.get("dog_vaccinated")),"dog_type":norm_choice(payload.get("dog_type"),dog_type_map,"stray"),"dog_behavior":norm_choice(payload.get("dog_behavior"),behavior_map,"calm"),"region_prevalence":norm_choice(payload.get("region_prevalence"),region_map,"unknown"),"bite_location":norm_choice(payload.get("bite_location"),location_map,"leg"),"bite_severity":norm_choice(payload.get("bite_severity"),severity_map,"scratch"),"previous_vaccine":norm_bool_str(payload.get("previous_vaccine")),"time_to_clean_minutes":coerce_positive_number(payload.get("time_to_clean_minutes"),default=30),"age":coerce_positive_number(payload.get("age"),default=30)}
def label_from_prob(p:float)->str:
    if p<0.34:return"Low"
    elif p<0.67:return"Medium"
    else:return"High"

# ------------------- LOGIN DECORATOR -------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ------------------- ROUTES -------------------

@app.route("/")
def home():
    return render_template("home.html", active_page='home')

@app.route("/predict", methods=["GET"])
@login_required
def predict_page():
    return render_template("index.html", active_page='predict')

@app.route("/predict", methods=["POST"])
@login_required 
def predict():
    try:
        if model is None: return jsonify({"success":False,"message":"Model not loaded"}),200
        if not request.is_json: return jsonify({"success":False,"message":"Content-Type must be application/json"}),200
        payload=request.get_json(silent=True)or{}
        x=preprocess_payload(payload)
        X=pd.DataFrame([x],columns=model_features)
        if hasattr(model,"predict_proba"):
            proba=model.predict_proba(X)[0]
            idx_high=1
            try:
                clf_classes=getattr(model,"classes_",None)
                if clf_classes is None and hasattr(model,"named_steps"):
                    clf_classes=model.named_steps[list(model.named_steps.keys())[-1]].classes_
                if clf_classes is not None:
                    idx_high=list(clf_classes).index("High")
            except Exception:pass
            p_high=float(proba[idx_high])
        else:
            if hasattr(model,"decision_function"):
                score=float(model.decision_function(X)[0])
                p_high=1.0/(1.0+math.exp(-score))
            else:
                pred=model.predict(X)[0]
                p_high=0.7 if str(pred)=="High"else 0.3
        return jsonify({"success":True,"risk":label_from_prob(p_high),"probability":round(float(p_high),4)}),200
    except Exception as e:
        app.logger.exception("Prediction failed")
        return jsonify({"success":False,"message":f"Prediction failed: {str(e)}"}),200

# ------------------- AUTH ROUTES -------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method=="POST":
        username=request.form.get("username")
        password=request.form.get("password")
        db=get_db()
        error=None
        if not username or not password:
            error="Username and password are required."
        else:
            user=db.execute("SELECT id FROM users WHERE username = ?",(username,)).fetchone()
            if user is not None:
                error=f"User {username} is already registered."
        if error is None:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",(username,generate_password_hash(password)),)
            db.commit()
            return redirect(url_for("login"))
        return render_template("signup.html",error=error)
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method=="POST":
        username=request.form.get("username")
        password=request.form.get("password")
        db=get_db()
        error=None
        user=db.execute("SELECT * FROM users WHERE username = ?",(username,)).fetchone()
        if user is None:
            error="Incorrect username."
        elif not check_password_hash(user["password_hash"],password):
            error="Incorrect password."
        if error is None:
            session.clear()
            session["user"]=user["username"]
            return redirect(url_for("home"))
        return render_template("login.html",error=error)
    return render_template("login.html")

# =======================================================
# == MODIFICATION: The dashboard route has been removed  ==
# =======================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ------------------- MAIN -------------------
if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000,debug=True)