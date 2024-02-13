import json
import pandas as pd
import os
from dotenv import load_dotenv
import requests
import re
load_dotenv()

# Retrieve values from the .env file
shopify_url = os.getenv("shopify_url")
store_name = os.getenv("store_name")
new_store_name = os.getenv("new_store_name")
local_delivery_enabled = os.getenv("local_delivery_enabled")
local_pickup_enabled = os.getenv("local_pickup_enabled")
current_quantity = os.getenv("current_quantity")
products_pages = 0
pages_data = []

# Allow the use of relative paths
os.chdir(os.path.dirname(__file__))
script_folder = os.path.dirname(__file__)
# Change the permissions of all files in the script's folder to allow all users to read and write to them
for file in os.listdir(script_folder):
    file_path = os.path.join(script_folder, file)
    os.chmod(file_path, 0o666)

def clean_filename(filename):
    # Remove invalid characters from the filename
    return re.sub(r'[\/:*?"<>|]', '', filename)

def get_products_json(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def save_to_file(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

api_url = f"https://{shopify_url}/products.json/?limit=250&page="
page_number = 1

# Create a set to store unique item names
unique_items = set()

# Create a list to store the data
rows = []

def convert_size(input_string):
    # Define the mapping of sizes
    size_mapping = {
        'xs': 'XS',
        'sm': 'S',
        'lg': 'L',
        'xl': 'XL',
        'xxl': 'XXL'
    }

    # Replace the sizes in the input string (case-insensitive)
    for size, replacement in size_mapping.items():
        input_string = re.sub(f'(?i){re.escape(size)}', replacement, input_string)

    print("replaced")
    print(input_string)

    return input_string


while True:
    products_data = get_products_json(api_url + str(page_number))
    if products_data and products_data.get("products"):
        save_to_file(products_data, f'products_page_{page_number}.json')
        #print(f"JSON data for page {page_number} saved to 'products_page_{page_number}.json'")

        # Process data for each product on the current page
        for product in products_data['products']:
            item_name = product['title']
            i = 0
            k = 0
            break_flag = False
            # Check if the item name is already processed
            if item_name not in unique_items and "Gift Card" not in item_name.title() and not "swag high" in item_name.lower():
                unique_items.add(item_name)
                while k < len(product["variants"]):
                    option_names = []
                    option_values = []
                    
                    if k < len(product["variants"]):
                        variant = product["variants"][k]
                        # Get Variant and SKU based on option values
                        sku = variant["sku"]
                        j = 1
                        #print("Variant")
                        #print(variant)
                        while j < 3:
                            variant_option = variant[f"option{j}"]
                            #print("\nVariant Option")
                            #print(variant_option)
                            if product["options"] and variant_option:
                                for option in product["options"]:
                                    if variant_option in option["values"]:
                                        if option["name"] != "Title":
                                            #print("\nChosen Name, and Option Match")
                                            #print(option["name"])
                                            #print(variant_option)
                                            option_names.append(option["name"])
                                            option_values.append(variant_option)
                            j += 1
                        #print("\nOption Names and Values")
                        #print(option_names)
                        #print(option_values)
                        k += 1
                        row_data = {
                            'Token': '',
                            'Item Name': item_name.title(),
                            'Variation Name': convert_size(variant['title'].title()) if variant and variant['title'] and variant['title'].title() != "Default Title" else "",
                            'SKU': sku,
                            'Description': product['body_html'],
                            'SEO Title': f"{item_name.title()} | {store_name}",
                            'SEO Description': product['body_html'] if product['body_html'] else '',
                            'Square Online Item Visibility': 'visible' if variant and variant['available'] else 'visible',
                            'Shipping Enabled': 'Y' if variant and variant['requires_shipping'] else 'N',
                            'Delivery Enabled': local_delivery_enabled,
                            'Pickup Enabled': local_pickup_enabled,
                            'Price': product['variants'][i]['price'] if product['variants'][i]['price'] else product['variants'][0]['price'] if product['variants'][0]['price'] else '0.00',
                            'Option Name 1': '',#option_names[0] if len(option_names) > 0 else '',
                            'Option Value 1': '',#option_values[0][:255] if len(option_values) > 0 else '',
                            'Option Name 2': '',#option_names[1] if len(option_names) > 1 else '',
                            'Option Value 2': '',#option_values[1][:255] if len(option_values) > 1 else '',
                            'Option Name 3': '',#option_names[2] if len(option_names) > 2 else '',
                            'Option Value 3': '',#option_values[2][:255] if len(option_values) > 2 else '',
                            f'Current Quantity {new_store_name}': current_quantity,
                            # Fill other fields with default values
                            'Category': product['product_type'],
                            'Permalink': product['handle'] if product['handle'] else '',
                            'Weight (kg)': (int(variant[0]['grams']/100)) if variant and variant['grams'] else '',
                            'Self-Serve Ordering Enabled': '',
                            'Online Sale Price': '',
                            'Sellable': 'Y',
                            'Stockable': 'Y',
                            'Skip Detail Screen in POS': 'N',
                            f'New Quantity {new_store_name}': '',
                            f'Stock Alert Enabled {new_store_name}': '',
                            f'Stock Alert Count {new_store_name}': ''
                        }
                        rows.append(row_data)
                        i += 1

                    

        page_number += 1
    else:
        print(f"No more items on page {page_number}")
        break

# Create a DataFrame from the list
df = pd.DataFrame(rows)

# Save DataFrame to Excel sheet
df.to_excel(r'output.xlsx', index=False)

# Create a folder for images
image_folder = f'{store_name}-images'
os.makedirs(image_folder, exist_ok=True)

# Download images and save to the folder
for i in range(1, page_number):
    with open(f'products_page_{i}.json', 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

        unique_items = set()
        for product in data['products']:
            item_name = product['title']
            category = product['product_type']

            # Check if the item name is already processed
            if item_name not in unique_items:
                unique_items.add(item_name)

                # Create folders based on category and item_name
                category_folder = os.path.join(image_folder, clean_filename(category))
                item_folder = os.path.join(category_folder, clean_filename(item_name))
                os.makedirs(item_folder, exist_ok=True)

                for i, image in enumerate(product['images']):
                    image_url = image['src']
                    image_name = clean_filename(f"{item_name.replace(' ', '_')}_{i+1}.png")  # Use underscores instead of spaces
                    image_path = os.path.join(item_folder, image_name)

                    print("Working...")

                    # Download the image
                    response = requests.get(image_url, verify=False)
                    with open(image_path, 'wb') as img_file:
                        img_file.write(response.content)
