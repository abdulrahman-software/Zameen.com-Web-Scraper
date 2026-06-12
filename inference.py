import json
from pyodide.http import open_url
from js import document

raw_json_data = open_url("model_data.json").read()
parsed_data = json.loads(raw_json_data)

MODEL_CONFIG = parsed_data["model"]
CATEGORICAL_ENCODERS = parsed_data["encoders"]
AVAILABLE_LOCATIONS = parsed_data["locations"]
AVAILABLE_PROPERTY_TYPES = parsed_data["prop_types"]

location_dropdown = document.getElementById("inp-location")
property_type_dropdown = document.getElementById("inp-type")

for location in AVAILABLE_LOCATIONS:
    dropdown_option = document.createElement("option")
    dropdown_option.value = location
    dropdown_option.textContent = location.split(",")[0].strip()
    location_dropdown.appendChild(dropdown_option)

for property_type in AVAILABLE_PROPERTY_TYPES:
    dropdown_option = document.createElement("option")
    dropdown_option.value = property_type
    dropdown_option.textContent = property_type
    property_type_dropdown.appendChild(dropdown_option)

def predict_tree(tree_data, input_features):
    current_node = 0
    children_left = tree_data["cl"]
    children_right = tree_data["cr"]
    feature_index = tree_data["f"]
    threshold_value = tree_data["th"]
    leaf_value = tree_data["v"]
    
    while children_left[current_node] != -1:
        if input_features[feature_index[current_node]] <= threshold_value[current_node]:
            current_node = children_left[current_node]
        else:
            current_node = children_right[current_node]
            
    return leaf_value[current_node]

def predict_gbr(input_dictionary):
    mapped_features = [input_dictionary[col] for col in MODEL_CONFIG["feature_cols"]]
    predicted_price = MODEL_CONFIG["init_prediction"]
    
    for tree_estimator in MODEL_CONFIG["estimators"]:
        predicted_price += MODEL_CONFIG["learning_rate"] * predict_tree(tree_estimator, mapped_features)
        
    return predicted_price

def encode_category(column_name, value):
    try:
        return CATEGORICAL_ENCODERS[column_name].index(value)
    except ValueError:
        return 0

def format_pkr(amount):
    if amount >= 1_000_000_000:
        return f"{amount/1_000_000_000:.2f} Arab"
    if amount >= 10_000_000:
        return f"{amount/10_000_000:.2f} Crore"
    if amount >= 100_000:
        return f"{amount/100_000:.2f} Lakh"
    return f"{amount:,.0f}"

predict_button = document.getElementById("predict-btn")
predict_button.disabled = False
predict_button.textContent = "Estimate Price"

status_indicator = document.getElementById("status-dot")
status_text_element = document.getElementById("status-text")
status_indicator.classList.add("ready")
status_text_element.textContent = "Python runtime ready"

document.getElementById("loader").classList.add("hidden")
document.getElementById("page").classList.add("visible")

def execute_prediction(event):
    error_element = document.getElementById("error-msg")
    error_element.style.display = "none"

    try:
        input_area = float(document.getElementById("inp-area").value)
        input_beds = float(document.getElementById("inp-beds").value)
        input_baths = float(document.getElementById("inp-baths").value)
    except ValueError:
        error_element.textContent = "Please fill in all fields with valid numbers."
        error_element.style.display = "block"
        return

    selected_location = document.getElementById("inp-location").value
    selected_type = document.getElementById("inp-type").value

    feature_payload = {
        "Area": input_area,
        "City": float(encode_category("City", "Islamabad")),
        "Bedrooms": input_beds,
        "Bathrooms": input_baths,
        "Location": float(encode_category("Location", selected_location)),
        "Property_Type": float(encode_category("Property_Type", selected_type)),
        "Built_in_year": 0.0,
        "Parking_space": 0.0,
        "Servant_Quarters": 0.0,
        "Store_rooms": 0.0,
        "Kitchens": 0.0,
        "Drawing_Rooms": 0.0,
    }

    final_price = predict_gbr(feature_payload)

    document.getElementById("res-formatted").textContent = format_pkr(final_price)
    document.getElementById("res-raw").textContent = f"PKR {final_price:,.0f}"
    document.getElementById("res-loc").textContent = selected_location.split(",")[0].strip()
    document.getElementById("res-type").textContent = selected_type
    document.getElementById("res-area").textContent = f"{input_area} Marla"
    document.getElementById("res-rooms").textContent = f"{int(input_beds)} / {int(input_baths)}"

    results_placeholder = document.getElementById("result-placeholder")
    results_content = document.getElementById("result-content")
    results_placeholder.style.display = "none"
    results_content.classList.remove("show")
    _ = results_content.offsetWidth 
    results_content.classList.add("show")

predict_button.onclick = execute_prediction
document.addEventListener("keydown", lambda e: execute_prediction(e) if e.key == "Enter" else None)