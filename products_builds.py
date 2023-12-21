import asyncio
import aiohttp
import aiofiles
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime
from urllib.parse import urlparse

async def fetch_product(session, product_id, operating_system, generation):
    url = f"https://content-system.gog.com/products/{product_id}/os/{operating_system}/builds?generation={generation}"
    async with session.get(url) as response:
        return await response.json()

def sanitize_filename(filename):
    # Replace special characters with underscores
    return filename.replace('/', '_').replace('?', '_').replace('=', '_')

async def download_and_save(session, product_id, operating_system, generation, semaphore, hashes, completed_tasks, max_retries=3):
    async with semaphore:
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Fetch product information
                product_data = await fetch_product(session, product_id, operating_system, generation)

                # Convert product_data to JSON string
                json_data = json.dumps(product_data, indent=2)

                # Calculate SHA-1 hash of the JSON data
                sha1_hash = hashlib.sha1(json_data.encode()).hexdigest()

                # Check if the file already exists in the hashes.json
                if product_id in hashes and hashes[product_id] == sha1_hash:
                    print(f"Product {product_id} already up-to-date. Skipping.")
                    return

                # Use a temporary folder for downloading and checking the hash
                temp_folder = os.path.join(os.environ['RUNNER_TEMP'], 'gog_products_temp', str(product_id))
                os.makedirs(temp_folder, exist_ok=True)

                temp_filename = os.path.join(temp_folder, f"{product_id}.json")

                async with aiofiles.open(temp_filename, 'w') as file:
                    await file.write(json_data)

                # Check the hash in the temporary folder
                with open(temp_filename, 'rb') as temp_file:
                    temp_hash = hashlib.sha1(temp_file.read()).hexdigest()

                # Delete the file and the temporary folder if the hash matches one of the specific hashes
                if temp_hash in ["1ec5694531870760d651960574b6332325773e1d", "7312b29e8a2172bfdcc278d012711a8caada90e2"]:
                    print(f"Product {product_id} has one of the specific hashes. Skipping saving and updating hashes.json.")
                    completed_tasks.append(product_id)
                    os.remove(temp_filename)
                    shutil.rmtree(temp_folder)  # Delete the temporary folder
                    return

                # Save the JSON data to the final destination with the folder structure
                folder_structure = f"products/{product_id}/os/{operating_system}/"
                final_filename = os.path.join(folder_structure, f"builds@generation={generation}")

                # Create directories if they don't exist
                os.makedirs(os.path.dirname(final_filename), exist_ok=True)

                # Move the file from the temporary folder to the final destination
                shutil.move(temp_filename, final_filename)

                # Update hashes.json with the full filename
                full_filename = sanitize_filename(f"{folder_structure}builds@generation={generation}")
                hashes[product_id] = sha1_hash
                if full_filename not in hashes:
                    hashes[full_filename] = sha1_hash

                print(f"Product {product_id} downloaded and saved successfully.")
                return

            except Exception as e:
                retry_count += 1
                print(f"Error downloading product {product_id}. Retrying... ({retry_count}/{max_retries})")
                print(f"Error details: {str(e)}")

        print(f"Failed to download product {product_id} after {max_retries} retries.")

async def main(start_product_id, end_product_id, operating_system, generation):
    semaphore = asyncio.Semaphore(500)  # Adjust the semaphore value as needed
    hashes = {}
    completed_tasks = []

    # Load existing hashes from hashes.json if it exists
    if os.path.exists('hashes.json'):
        with open('hashes.json', 'r') as hash_file:
            hashes = json.load(hash_file)

    async with aiohttp.ClientSession() as session:
        tasks = [download_and_save(session, product_id, operating_system, generation, semaphore, hashes, completed_tasks) for product_id in range(start_product_id, end_product_id + 1)]
        await asyncio.gather(*tasks)

    sorted_hashes = {}
    for original_key, value in sorted(hashes.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else float('inf')):
        if str(original_key).isdigit():
            sorted_key = f"products/{original_key}/os/{operating_system}/builds@generation={generation}"
            sorted_hashes[sorted_key] = value
        
    with open('hashes.json', 'w') as hash_file:
        json.dump(sorted_hashes, hash_file, indent=2)

    # Git commands to add, commit, and push changes
    if completed_tasks:
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", f"Updated DB as of - {datetime.now()}"])
        subprocess.run(["git", "push"])

if __name__ == "__main__":
    start_product_id = 938000000  # Replace with your start product ID
    end_product_id = 939000000   # Replace with your end product ID
    os_type = "windows"   # Replace with your operating system
    generation = 2        # Replace with your generation
    asyncio.run(main(start_product_id, end_product_id, os_type, generation))
