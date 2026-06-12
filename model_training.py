import re
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
from catboost import CatBoostRegressor

property_data = pd.read_csv('islamabad_properties.csv')
property_data.drop_duplicates(inplace=True)

def convert_pakistani_currency_to_numeric(currency_string):
    if pd.isna(currency_string) or currency_string == '-':
        return np.nan
    cleaned_string = str(currency_string).lower().replace(',', '').strip()
    try:
        base_value = float(cleaned_string.split()[0])
        if 'arab' in cleaned_string: return base_value * 1_000_000_000
        if 'crore' in cleaned_string: return base_value * 10_000_000
        if 'lakh' in cleaned_string: return base_value * 100_000
        return base_value
    except ValueError:
        return np.nan

def normalize_property_area_to_marla(area_string):
    if pd.isna(area_string) or area_string == '-':
        return np.nan
    cleaned_string = str(area_string).lower().strip()
    try:
        area_value = float(cleaned_string.split()[0])
        return area_value * 20.0 if 'kanal' in cleaned_string else area_value
    except ValueError:
        return np.nan

def extract_numerical_room_count(room_string):
    if pd.isna(room_string) or room_string == '-':
        return np.nan
    try:
        return float(str(room_string).split()[0])
    except ValueError:
        return np.nan

def extract_year_from_string(year_string):
    if pd.isna(year_string) or year_string == '-':
        return np.nan
    match = re.search(r'\d{4}', str(year_string))
    return float(match.group()) if match else np.nan

property_data['Price'] = property_data['Price'].apply(convert_pakistani_currency_to_numeric)
property_data['Area'] = property_data['Area'].apply(normalize_property_area_to_marla)
property_data['Bedrooms'] = property_data['Bedrooms'].apply(extract_numerical_room_count)
property_data['Bathrooms'] = property_data['Bathrooms'].apply(extract_numerical_room_count)
property_data['Built_in_year'] = property_data['Built_in_year'].apply(extract_year_from_string)

property_data.dropna(subset=['Price', 'Area', 'Location'], inplace=True)
property_data['Bedrooms'] = property_data['Bedrooms'].fillna(property_data['Bedrooms'].median())
property_data['Bathrooms'] = property_data['Bathrooms'].fillna(property_data['Bathrooms'].median())

amenity_columns = ['Built_in_year', 'Parking_space', 'Servant_Quarters', 'Store_rooms', 'Kitchens', 'Drawing_Rooms']
property_data[amenity_columns] = property_data[amenity_columns].fillna(0)

label_encoders = {}
for category_column in ['Location', 'Property_Type', 'City']:
    encoder = LabelEncoder()
    property_data[category_column] = encoder.fit_transform(property_data[category_column].astype(str))
    label_encoders[category_column] = encoder

X_features = property_data.drop('Price', axis=1)
y_target = property_data['Price']

X_train, X_test, y_train, y_test = train_test_split(X_features, y_target, test_size=0.2, random_state=42)

models_dictionary = {
    'Linear Regression': LinearRegression(),
    'Decision Tree': DecisionTreeRegressor(random_state=42),
    'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
    'XGBoost': XGBRegressor(n_estimators=100, random_state=42, verbosity=0),
    'CatBoost': CatBoostRegressor(iterations=100, random_seed=42, verbose=0),
}

evaluation_results = []
trained_models = {}

print(f"\n{'Model':<22} {'MAE':>14} {'MSE':>20} {'RMSE':>14} {'R2':>8}")
print("-" * 82)

for model_name, model_instance in models_dictionary.items():
    model_instance.fit(X_train, y_train)
    predictions = model_instance.predict(X_test)

    mean_abs_error = mean_absolute_error(y_test, predictions)
    mean_sq_error = mean_squared_error(y_test, predictions)
    root_mean_sq_error = np.sqrt(mean_sq_error)
    r2_metric = r2_score(y_test, predictions)

    evaluation_results.append({
        'Model': model_name,
        'MAE': round(mean_abs_error, 2),
        'MSE': round(mean_sq_error, 2),
        'RMSE': round(root_mean_sq_error, 2),
        'R2': round(r2_metric, 4)
    })
    trained_models[model_name] = model_instance

    print(f"{model_name:<22} {mean_abs_error:>14,.0f} {mean_sq_error:>20,.0f} {root_mean_sq_error:>14,.0f} {r2_metric:>8.4f}")

results_dataframe = pd.DataFrame(evaluation_results).sort_values('R2', ascending=False)
results_dataframe.to_csv('model_results.csv', index=False)

best_model_name = results_dataframe.iloc[0]['Model']
best_model_instance = trained_models[best_model_name]
print(f"\nBest model: {best_model_name} (R2 = {results_dataframe.iloc[0]['R2']})")

def serialize_gbr_to_json(gradient_boosting_model, feature_columns, encoders_dict, unique_locations, unique_property_types):
    def serialize_tree(tree_instance):
        return {
            'cl': tree_instance.children_left.tolist(),
            'cr': tree_instance.children_right.tolist(),
            'f':  tree_instance.feature.tolist(),
            'th': tree_instance.threshold.tolist(),
            'v':  tree_instance.value[:, 0, 0].tolist(),
        }

    return {
        'model': {
            'learning_rate': gradient_boosting_model.learning_rate,
            'init_prediction': float(gradient_boosting_model.init_.constant_[0][0]),
            'estimators': [serialize_tree(estimator[0].tree_) for estimator in gradient_boosting_model.estimators_],
            'feature_cols': list(feature_columns),
        },
        'encoders': {col: encoder.classes_.tolist() for col, encoder in encoders_dict.items()},
        'locations': unique_locations,
        'prop_types': unique_property_types,
    }

raw_dataset = pd.read_csv('islamabad_properties.csv')
raw_dataset.dropna(subset=['Location'], inplace=True)

export_encoders = {}
for category_column in ['Location', 'Property_Type', 'City']:
    export_encoder = LabelEncoder()
    export_encoder.fit(raw_dataset[category_column].astype(str))
    export_encoders[category_column] = export_encoder

exported_locations = sorted(raw_dataset['Location'].dropna().unique().tolist())
exported_property_types = sorted(raw_dataset['Property_Type'].dropna().unique().tolist())

json_payload = serialize_gbr_to_json(best_model_instance, X_features.columns, export_encoders, exported_locations, exported_property_types)

with open('model_data.json', 'w') as json_file:
    json.dump(json_payload, json_file)

payload_size_kb = len(json.dumps(json_payload)) / 1024
print(f"Exported model_data.json ({payload_size_kb:.1f} KB) — use with index.html, no pkl needed")
print("Full results saved to model_results.csv")