# app.py
from flask import Flask, request, jsonify, render_template
import joblib
import numpy as np
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

MODEL_PATH = 'model.joblib'
model = joblib.load(MODEL_PATH)

# helper to build input for the pipeline (pandas-like dict accepted by pipeline)
def build_input(data):
    # expected fields:
    # dog_vaccinated, dog_type, bite_location, bite_severity,
    # time_to_clean_minutes, age, previous_vaccine, dog_behavior, region_prevalence
    # We'll coerce types and provide defaults if missing.
    input_row = {
        'dog_vaccinated': data.get('dog_vaccinated', 'No'),
        'dog_type': data.get('dog_type', 'Stray'),
        'bite_location': data.get('bite_location', 'Leg'),
        'bite_severity': data.get('bite_severity', 'Superficial bite'),
        'time_to_clean_minutes': int(data.get('time_to_clean_minutes', 30)),
        'age': int(data.get('age', 30)),
        'previous_vaccine': data.get('previous_vaccine', 'No'),
        'dog_behavior': data.get('dog_behavior', 'Calm'),
        'region_prevalence': data.get('region_prevalence', 'Low'),
    }
    return input_row


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    # accept JSON or form
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    # Build single-row data
    row = build_input(data)

    # The pipeline expects a 2D structure (DataFrame), but sklearn pipeline can accept a list of dicts if consistent.
    # We'll pass a list with one dict via the pipeline's preprocessing.
    try:
        proba = model.predict_proba([list(row.values())])  # fallback — but our pipeline expects column order; safer to use DataFrame
    except Exception:
        # safer route: build DataFrame in proper column order
        import pandas as pd
        df = pd.DataFrame([row])
        proba = model.predict_proba(df)

    # predict_proba returns array [[prob_low, prob_high]] if classes are ['Low','High']
    # find index of 'High' to return correct probability
    classes = model.classes_
    if 'High' in classes:
        high_index = list(classes).index('High')
    else:
        # fallback assume second index is High
        high_index = 1

    high_prob = float(proba[0][high_index])
    pred_label = 'High' if high_prob >= 0.5 else 'Low'

    return jsonify({
        'risk': pred_label,
        'probability': round(high_prob, 4)
    })


if __name__ == '__main__':
    # run on localhost:5000
    app.run(debug=True)
