import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

property_data = pd.read_csv('islamabad_properties.csv')

property_data.drop_duplicates(inplace=True)

def convert_pakistani_currency_to_numeric(currency_string):
    if pd.isna(currency_string) or currency_string == '-': 
        return np.nan
    sanitized_currency_string = str(currency_string).lower().replace(',', '').strip()
    try:
        numeric_base_value = float(sanitized_currency_string.split()[0])
        if 'arab' in sanitized_currency_string: 
            return numeric_base_value * 1000000000
        if 'crore' in sanitized_currency_string: 
            return numeric_base_value * 10000000
        if 'lakh' in sanitized_currency_string: 
            return numeric_base_value * 100000
        return numeric_base_value
    except ValueError: 
        return np.nan

def normalize_property_area_to_marla(area_string):
    if pd.isna(area_string) or area_string == '-': 
        return np.nan
    sanitized_area_string = str(area_string).lower().strip()
    try:
        numeric_area_value = float(sanitized_area_string.split()[0])
        if 'kanal' in sanitized_area_string: 
            return numeric_area_value * 20.0
        return numeric_area_value
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
    import re
    match = re.search(r'\d{4}', str(year_string))
    return float(match.group()) if match else np.nan

property_data['Price'] = property_data['Price'].apply(convert_pakistani_currency_to_numeric)
property_data['Area'] = property_data['Area'].apply(normalize_property_area_to_marla)
property_data['Bedrooms'] = property_data['Bedrooms'].apply(extract_numerical_room_count)
property_data['Bathrooms'] = property_data['Bathrooms'].apply(extract_numerical_room_count)
property_data['Built_in_year'] = property_data['Built_in_year'].apply(extract_year_from_string)

property_data.dropna(subset=['Price', 'Area', 'Location'], inplace=True)

median_bedroom_count = property_data['Bedrooms'].median()
median_bathroom_count = property_data['Bathrooms'].median()

property_data['Bedrooms'] = property_data['Bedrooms'].fillna(median_bedroom_count)
property_data['Bathrooms'] = property_data['Bathrooms'].fillna(median_bathroom_count)

count_amenity_columns = ['Parking_space', 'Servant_Quarters', 'Store_rooms', 'Kitchens', 'Drawing_Rooms']
property_data[count_amenity_columns] = property_data[count_amenity_columns].fillna(0)

label_encoders = {}
target_categorical_columns = ['Location', 'Property_Type', 'City']

for column_name in target_categorical_columns:
    le = LabelEncoder()
    property_data[column_name] = le.fit_transform(property_data[column_name].astype(str))
    label_encoders[column_name] = le

independent_features_matrix = property_data.drop('Price', axis=1)
dependent_target_vector = property_data['Price']

features_train, features_test, target_train, target_test = train_test_split(
    independent_features_matrix, 
    dependent_target_vector, 
    test_size=0.2, 
    random_state=42
)

print(f"Total records after duplicate removal and cleaning: {len(property_data)}")
print(f"Training features shape: {features_train.shape}")
print(f"Testing features shape: {features_test.shape}")