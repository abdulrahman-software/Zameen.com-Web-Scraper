import os
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CONFIG = {
    "base_domain": "https://www.zameen.com",
    "link_prefix": "/Property/",
    "search_url_template": "https://www.zameen.com/Homes/Islamabad-3-{page}.html",
    "link_selector": "a[href*='/Property/']",
    "content_anchor_selector": "[aria-label='Price']",
    "validation_selectors": ["[aria-label='Purpose']", "[aria-label='Price']"],
    "rejection_keywords": ["rent", "month"],
    "primary_key": "Price",
    "schema_fields": [
        "Price", "Area", "City", "Bedrooms", "Bathrooms",
        "Location", "Property_Type", "Built_in_year",
        "Parking_space", "Servant_Quarters", "Store_rooms",
        "Kitchens", "Drawing_Rooms",
    ],
    "default_values": {"City": "Islamabad"},
    "core_selectors": {
        "Price":         "[aria-label='Price']",
        "Area":          "[aria-label='Area']",
        "Bedrooms":      "[aria-label='Beds']",
        "Bathrooms":     "[aria-label='Baths']",
        "Location":      "[aria-label='Location']",
        "Property_Type": "[aria-label='Type']",
    },
    "list_item_selector": "ul[aria-label='Property details'] li",
    "list_text_mappings": {
        "built in year":   "Built_in_year",
        "parking space":   "Parking_space",
        "servant quarter": "Servant_Quarters",
        "store room":      "Store_rooms",
        "kitchen":         "Kitchens",
        "drawing room":    "Drawing_Rooms",
    },
    "max_retries": 2,
}

URLS_CACHE  = "urls.txt"
OUTPUT_CSV  = "islamabad_properties.csv"
TARGET      = 350
WORKERS     = 10

def gather_urls(target_count):
    discovered_urls = set()

    with sync_playwright() as playwright_instance:
        browser_instance = playwright_instance.chromium.launch(headless=False)
        browser_context = browser_instance.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 720},
        )
        current_page = browser_context.new_page()
        page_number = 1

        while len(discovered_urls) < target_count:
            target_url = CONFIG["search_url_template"].format(page=page_number)
            print(f"  Search page {page_number}...")
            try:
                current_page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                page_title = current_page.title().lower()
                if any(keyword in page_title for keyword in ("moment", "challenge", "cloudflare", "security")):
                    input("\n[!] Bot challenge — solve it in the browser then press ENTER.\n> ")

                anchor_elements = current_page.query_selector_all(CONFIG["link_selector"])
                urls_before_extraction = len(discovered_urls)
                
                for element in anchor_elements:
                    hyperlink = element.get_attribute("href")
                    if hyperlink and "/Property/" in hyperlink:
                        sanitized_url = hyperlink.split("?")[0]
                        if not sanitized_url.startswith("http"):
                            sanitized_url = CONFIG["base_domain"] + sanitized_url
                        discovered_urls.add(sanitized_url)

                if len(discovered_urls) == urls_before_extraction:
                    print("  No new URLs — stopping pagination.")
                    break
            except Exception as navigation_error:
                print(f"  Page {page_number} error: {navigation_error}")

            page_number += 1
            time.sleep(random.uniform(1.5, 3.0))

        browser_instance.close()

    final_url_list = list(discovered_urls)[:target_count]
    with open(URLS_CACHE, "w") as file_object:
        file_object.write("\n".join(final_url_list))
    print(f"  Saved {len(final_url_list)} URLs to {URLS_CACHE}\n")
    
    return final_url_list

def extract_one(target_url, playwright_page):
    request_session = requests.Session()
    request_session.headers.update(HEADERS)

    for attempt_number in range(1, CONFIG["max_retries"] + 1):
        try:
            http_response = request_session.get(target_url, timeout=20)
            if http_response.status_code != 200:
                continue

            playwright_page.set_content(http_response.text, wait_until="domcontentloaded")

            anchor_element = playwright_page.query_selector(CONFIG["content_anchor_selector"])
            if not anchor_element:
                print(f"  Attempt {attempt_number}: content anchor not found, retrying...")
                continue

            is_rejected = False
            for validation_selector in CONFIG["validation_selectors"]:
                validation_element = playwright_page.query_selector(validation_selector)
                if validation_element:
                    element_text = validation_element.inner_text().strip().lower()
                    if any(keyword in element_text for keyword in CONFIG["rejection_keywords"]):
                        is_rejected = True
                        break
            if is_rejected:
                return None

            property_record = {field_key: None for field_key in CONFIG["schema_fields"]}
            for default_key, default_value in CONFIG["default_values"].items():
                property_record[default_key] = default_value

            for core_field, core_selector in CONFIG["core_selectors"].items():
                core_element = playwright_page.query_selector(core_selector)
                if core_element:
                    property_record[core_field] = core_element.inner_text().strip()

            list_elements = playwright_page.locator(CONFIG["list_item_selector"]).all_inner_texts()

            for item_text in list_elements:
                normalized_text = item_text.lower()
                for match_string, mapped_field in CONFIG["list_text_mappings"].items():
                    if match_string in normalized_text and not property_record.get(mapped_field):
                        property_record[mapped_field] = item_text.strip()

            return property_record

        except Exception as extraction_error:
            print(f"  Attempt {attempt_number} failed for {target_url}: {extraction_error}")
            if attempt_number < CONFIG["max_retries"]:
                time.sleep(random.uniform(1.0, 2.0))

    return None

def worker_thread(url_chunk):
    extracted_records = []
    with sync_playwright() as playwright_instance:
        browser_instance = playwright_instance.chromium.launch(headless=True)
        worker_page = browser_instance.new_page()

        for target_url in url_chunk:
            record_data = extract_one(target_url, worker_page)
            extracted_records.append((target_url, record_data))

        browser_instance.close()
    return extracted_records

def parallel_extract(url_list, total_workers):
    chunk_size = max(1, len(url_list) // total_workers)
    url_chunks = [url_list[index:index + chunk_size] for index in range(0, len(url_list), chunk_size)]

    validated_records = []
    completed_tasks = 0
    total_tasks = len(url_list)

    with ThreadPoolExecutor(max_workers=total_workers) as thread_pool:
        future_tasks = [thread_pool.submit(worker_thread, chunk) for chunk in url_chunks]
        for completed_future in as_completed(future_tasks):
            for target_url, record_data in completed_future.result():
                completed_tasks += 1
                if record_data and record_data.get(CONFIG["primary_key"]):
                    validated_records.append(record_data)
                    print(f"[{completed_tasks}/{total_tasks}] OK    {target_url}")
                else:
                    print(f"[{completed_tasks}/{total_tasks}] SKIP  {target_url}")

    return validated_records

def main():
    if os.path.exists(URLS_CACHE):
        with open(URLS_CACHE) as file_object:
            url_list = [line.strip() for line in file_object if line.strip()]
        print(f"Loaded {len(url_list)} URLs from {URLS_CACHE}. Delete it to re-gather.\n")
    else:
        print("Gathering URLs...")
        url_list = gather_urls(TARGET)

    print(f"Extracting {len(url_list)} pages using {WORKERS} parallel workers...\n")
    final_records = parallel_extract(url_list, WORKERS)

    dataframe = pd.DataFrame(final_records, columns=CONFIG["schema_fields"])
    dataframe.to_csv(OUTPUT_CSV, index=False)
    print(f"\nDone. {len(final_records)} records saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main() 