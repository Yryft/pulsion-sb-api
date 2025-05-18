import requests, zipfile, io, shutil, re, json, os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://api.hypixel.net/skyblock/bazaar"

repo = "NotEnoughUpdates/NotEnoughUpdates-REPO"
branch = "master"
folder_to_extract = "items"
# Path to the folder containing the JSON files
folder_path = "NotEnoughUpdates-REPO-master/items"

zip_url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
# Output dictionary
output = {}


def get_neu_data():
    # Download and extract only the folder
    print("Downloading NEU's REPO...")
    response = requests.get(zip_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        print("Extracting...")
        for member in zip_ref.namelist():
            if member.startswith(f"{repo.split('/')[-1]}-{branch}/{folder_to_extract}"):
                zip_ref.extract(member)
        print(".json files downloaded !")


def jsons():
    # Worker to process individual JSON files
    def process_file(filename):
        if not filename.endswith('.json'):
            return None
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            print(f"Error decoding or opening JSON in file: {filename}")
            return None

        item_id = data.get('internalname', '')
        name = data.get('displayname', '')
        if not item_id:
            return None

        # replace underscores and semicolons with spaces, then title-case
        if 'Enchanted Book' in name:
            name = item_id.replace('_', ' ').replace(';', ' ').title()
            # remove 'Ultimate' except for the special ULTIMATE_WISE book
            if 'ULTIMATE_WISE' not in item_id:
                name = name.replace('Ultimate ', '')

        return item_id, name

    # Use a thread pool to speed up file processing
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        futures = {executor.submit(process_file, fn): fn for fn in os.listdir(folder_path)}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                item_id, name = result
                output[item_id] = { 'name': name }

    # Save to a single JSON file
    output_path = 'items.json'
    with open(output_path, 'w', encoding='utf-8') as outfile:
        json.dump(output, outfile, indent=4)

    print('Succès : items.json mis à jour.')
    shutil.rmtree('NotEnoughUpdates-REPO-master')
    print('Succès : NotEnoughUpdates-REPO-master supprimé.')
    

get_neu_data()
jsons()
input("\n\nAppuie sur Entrée pour quitter...")
