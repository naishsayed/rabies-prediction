# backend/train_model.py
import os
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from sklearn.ensemble import GradientBoostingClassifier  # robust on tabular

rng = np.random.default_rng(42)

def generate_synthetic(n=4000):
    dog_vaccinated = rng.choice(["Yes","No","Unknown"], n, p=[0.45, 0.4, 0.15])
    dog_type = rng.choice(["Stray","Pet","Wild"], n, p=[0.55, 0.35, 0.10])
    dog_behavior = rng.choice(["Calm","Aggressive","Sick","Playful","Unusual Movements"], n,
                              p=[0.35,0.30,0.15,0.10,0.10])
    region_prevalence = rng.choice(["Low","Medium","High","Unknown"], n, p=[0.35,0.35,0.25,0.05])
    bite_location = rng.choice(["Leg","Arm","Hand","Finger","Face","Neck","Torso"], n,
                               p=[0.30,0.25,0.15,0.10,0.08,0.07,0.05])
    bite_severity = rng.choice(["Scratch","Superficial bite","Deep bite","Multiple deep wounds","Severe tissue damage"], n,
                               p=[0.35,0.30,0.20,0.10,0.05])
    time_to_clean_minutes = np.maximum(0, rng.normal(40, 25, n).round().astype(int))
    age = np.clip(rng.normal(32, 16, n).round().astype(int), 1, 90)
    previous_vaccine = rng.choice(["Yes","No","Unknown"], n, p=[0.25,0.65,0.10])

    base = (
        0.9 * (dog_type == "Wild") +
        0.7 * (dog_type == "Stray") +
        0.6 * (dog_behavior == "Aggressive") +
        0.7 * (dog_behavior == "Sick") +
        0.5 * (dog_behavior == "Unusual Movements") +
        0.6 * (region_prevalence == "High") +
        0.4 * (bite_location == "Face") + 0.35 * (bite_location == "Neck") +
        0.55 * (bite_severity == "Deep bite") +
        0.8 * (bite_severity == "Multiple deep wounds") +
        1.0 * (bite_severity == "Severe tissue damage") +
        0.004 * np.maximum(0, time_to_clean_minutes - 15) +
        0.15 * (age < 10) + 0.12 * (age > 60) +
        0.25 * (previous_vaccine == "No") +
        0.10 * (dog_vaccinated == "No")
    )

    base -= 0.25 * (dog_vaccinated == "Yes")
    base -= 0.35 * (previous_vaccine == "Yes")

    prob_high = 1 / (1 + np.exp(-(base - 1.2)))
    risk = np.where(rng.random(n) < prob_high, "High", "Low")

    df = pd.DataFrame({
        "dog_vaccinated": dog_vaccinated,
        "dog_type": dog_type,
        "dog_behavior": dog_behavior,
        "region_prevalence": region_prevalence,
        "bite_location": bite_location,
        "bite_severity": bite_severity,
        "previous_vaccine": previous_vaccine,
        "time_to_clean_minutes": time_to_clean_minutes,
        "age": age,
        "risk": risk
    })

    # Ensure same column order as app.py expects
    df = df[[
        "dog_vaccinated", "dog_type", "dog_behavior", "region_prevalence",
        "bite_location", "bite_severity", "previous_vaccine",
        "time_to_clean_minutes", "age", "risk"
    ]]

    return df

def train_and_save(df: pd.DataFrame, out_path: str):
    X = df.drop(columns=["risk"])
    y = df["risk"]

    cat_cols = [
        "dog_vaccinated","dog_type","dog_behavior","region_prevalence",
        "bite_location","bite_severity","previous_vaccine"
    ]
    num_cols = ["time_to_clean_minutes","age"]

    pre = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
            ("num", "passthrough", num_cols),
        ]
    )

    clf = GradientBoostingClassifier(random_state=42)
    pipe = Pipeline(steps=[("pre", pre), ("clf", clf)])

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipe.fit(Xtr, ytr)

    pred = pipe.predict(Xte)
    print(classification_report(yte, pred))

    dump(pipe, out_path)
    print(f"Saved model to: {out_path}")

if __name__ == "__main__":
    df = generate_synthetic(n=6000)
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    OUT = os.path.join(APP_DIR, "model.joblib")
    train_and_save(df, OUT)
