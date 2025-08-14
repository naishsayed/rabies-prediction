# train_model.py
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import random

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)
random.seed(RANDOM_STATE)


def generate_synthetic_data(n=2000):
    dog_vaccinated = np.random.choice(['Yes', 'No'], size=n, p=[0.35, 0.65])  # many dogs unvaccinated
    dog_type = np.random.choice(['Stray', 'Pet'], size=n, p=[0.6, 0.4])
    bite_location = np.random.choice(['Face','Neck','Hand','Arm','Leg','Finger'], size=n,
                                     p=[0.05,0.03,0.25,0.2,0.35,0.12])
    bite_severity = np.random.choice(['Scratch','Superficial bite','Deep bite','Multiple deep wounds'],
                                     size=n, p=[0.3,0.35,0.28,0.07])
    time_to_clean = np.random.exponential(scale=60, size=n).astype(int)  # minutes; many small, some large
    time_to_clean = np.clip(time_to_clean, 0, 1440)  # up to a day
    age = np.random.choice(range(1, 90), size=n, p=np.repeat(1/89, 89))
    previous_vaccine = np.random.choice(['Yes','No'], size=n, p=[0.12, 0.88])
    dog_behavior = np.random.choice(['Aggressive','Calm','Sick','Playful'], size=n, p=[0.25,0.55,0.15,0.05])
    region_prevalence = np.random.choice(['Low','Medium','High'], size=n, p=[0.5,0.35,0.15])

    df = pd.DataFrame({
        'dog_vaccinated': dog_vaccinated,
        'dog_type': dog_type,
        'bite_location': bite_location,
        'bite_severity': bite_severity,
        'time_to_clean_minutes': time_to_clean,
        'age': age,
        'previous_vaccine': previous_vaccine,
        'dog_behavior': dog_behavior,
        'region_prevalence': region_prevalence,
    })

    # Heuristic to compute label probability (not perfect, but realistic)
    def row_to_prob(r):
        base = 0.05
        # location: face/neck much riskier
        if r['bite_location'] in ('Face','Neck'):
            base += 0.45
        elif r['bite_location'] in ('Hand','Finger'):
            base += 0.18
        elif r['bite_location'] in ('Arm','Leg'):
            base += 0.08

        # severity
        if r['bite_severity'] == 'Multiple deep wounds':
            base += 0.25
        elif r['bite_severity'] == 'Deep bite':
            base += 0.18
        elif r['bite_severity'] == 'Superficial bite':
            base += 0.07
        else:
            base += 0.02

        # dog vaccinated reduces risk
        if r['dog_vaccinated'] == 'Yes':
            base -= 0.25
        # previous vaccine reduces risk
        if r['previous_vaccine'] == 'Yes':
            base -= 0.30

        # time to clean: each hour adds ~0.03
        base += min(0.6, (r['time_to_clean_minutes'] / 60) * 0.03)

        # dog behavior
        if r['dog_behavior'] == 'Sick':
            base += 0.18
        if r['dog_behavior'] == 'Aggressive':
            base += 0.09

        # region prevalence
        if r['region_prevalence'] == 'High':
            base += 0.12
        elif r['region_prevalence'] == 'Medium':
            base += 0.06

        # clamp
        base = max(0.01, min(0.99, base))
        return base

    probs = df.apply(row_to_prob, axis=1)
    # Convert to label with noise
    labels = (np.random.rand(len(probs)) < probs).astype(int)  # 1 = High risk, 0 = Low risk
    df['risk'] = np.where(labels==1, 'High', 'Low')
    return df


def train_and_save(df, save_path='model.joblib'):
    # features and target
    X = df.drop('risk', axis=1)
    y = df['risk']

    # categorical and numerical columns
    categorical_cols = ['dog_vaccinated','dog_type','bite_location','bite_severity','previous_vaccine','dog_behavior','region_prevalence']
    numeric_cols = ['time_to_clean_minutes','age']

    # Preprocessing
    cat_pipe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    preprocessor = ColumnTransformer([
        ('cat', cat_pipe, categorical_cols),
        ('num', StandardScaler(), numeric_cols)
    ], remainder='drop')

    # Pipeline
    pipeline = Pipeline([
        ('pre', preprocessor),
        ('clf', RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE, class_weight='balanced'))
    ])

    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y)

    pipeline.fit(X_train, y_train)

    # Evaluate
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]  # probability for 'High' class may need mapping
    print("Classification report (test):")
    print(classification_report(y_test, y_pred, digits=4))
    try:
        auc = roc_auc_score((y_test=='High').astype(int), y_prob)
        print("ROC AUC:", auc)
    except Exception:
        pass

    # Save pipeline
    joblib.dump(pipeline, save_path)
    print(f"Saved trained pipeline to {save_path}")

    # Save a small sample of dataset for later reference
    df.to_csv('dataset_synthetic.csv', index=False)
    print("Saved dataset as dataset_synthetic.csv")


if __name__ == "__main__":
    print("Generating synthetic dataset...")
    df = generate_synthetic_data(n=2000)
    print("Distribution of labels:")
    print(df['risk'].value_counts(normalize=True))
    train_and_save(df, save_path='model.joblib')
