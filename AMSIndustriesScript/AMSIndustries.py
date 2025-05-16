import requests
import os
import time
import csv
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dotenv import load_dotenv

# This function looks for known industry names in the model's response text.
# If a known industry is mentioned, it returns that industry; otherwise, it returns "Unknown".
def extract_industry(text):
    industries = [
        "Bau, Baunebengewerbe, Holz, Gebäudetechnik",
        "Bergbau, Rohstoffe, Glas, Keramik, Stein",
        "Büro, Marketing, Finanz, Recht, Sicherheit",
        "Chemie, Biotechnologie, Lebensmittel, Kunststoffe",
        "Elektrotechnik, Elektronik, Telekommunikation, IT",
        "Handel, Logistik, Verkehr",
        "Landwirtschaft, Gartenbau, Forstwirtschaft",
        "Maschinenbau, Kfz, Metall",
        "Medien, Grafik, Design, Druck, Kunst, Kunsthandwerk",
        "Reinigung, Hausbetreuung, Anlern- und Hilfsberufe",
        "Soziales, Gesundheit, Schönheitspflege",
        "Textil und Bekleidung, Mode, Leder",
        "Tourismus, Gastgewerbe, Freizeit",
        "Umwelt",
        "Wissenschaft, Bildung, Forschung und Entwicklung"
    ]
    
    # Convert text to lowercase for case-insensitive comparison
    text_lower = text.lower()
    
    # First try exact matches
    for industry in industries:
        if industry.lower() in text_lower:
            return industry
    
    # If no exact match, try matching by first word or key terms
    for industry in industries:
        # Split the industry into its components
        components = [comp.strip().lower() for comp in industry.split(',')]
        # Check if any component is mentioned in the text
        if any(comp in text_lower for comp in components):
            return industry
    
    return "Unknown"

# API key
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model
MODEL = "x-ai/grok-3-mini-beta"

# Shared variable to track the last request time
last_request_time = time.time()

def send_prompt(prompt_data):
    global last_request_time
    
    prompt, params = prompt_data
    
    # Rate limiting
    current_time = time.time()
    time_since_last_request = current_time - last_request_time
    if time_since_last_request < 0.053:  # ~19 requests per second
        time.sleep(0.053 - time_since_last_request)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "My Prompt Tool"
    }

    data = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=15)
        last_request_time = time.time()
        
        if response.status_code == 200:
            output = response.json()
            if "choices" in output and len(output["choices"]) > 0:
                response_text = output["choices"][0]["message"]["content"]
                return response_text, params
            else:
                print(f"\nWarning: No choices in response for request {params['request_number']}")
                print(f"Response content: {output}")
                return None, params
        else:
            print(f"\nError: Status code {response.status_code} for request {params['request_number']}")
            print(f"Response: {response.text}")
            return None, params
    except Exception as e:
        print(f"\nError in request {params['request_number']}: {e}")
        return None, params

if __name__ == "__main__":
    start_time = time.time()
    
    num_requests = 10 
    
    # Base industry list
    industries = [
        "Bau, Baunebengewerbe, Holz, Gebäudetechnik",
        "Bergbau, Rohstoffe, Glas, Keramik, Stein",
        "Büro, Marketing, Finanz, Recht, Sicherheit",
        "Chemie, Biotechnologie, Lebensmittel, Kunststoffe",
        "Elektrotechnik, Elektronik, Telekommunikation, IT",
        "Handel, Logistik, Verkehr",
        "Landwirtschaft, Gartenbau, Forstwirtschaft",
        "Maschinenbau, Kfz, Metall",
        "Medien, Grafik, Design, Druck, Kunst, Kunsthandwerk",
        "Reinigung, Hausbetreuung, Anlern- und Hilfsberufe",
        "Soziales, Gesundheit, Schönheitspflege",
        "Textil und Bekleidung, Mode, Leder",
        "Tourismus, Gastgewerbe, Freizeit",
        "Umwelt",
        "Wissenschaft, Bildung, Forschung und Entwicklung"
    ]
    
    # Prepare all prompts
    all_prompts = []
    
    print("Preparing prompts...")
    
    # Add default prompts with randomized industry order
    for i in range(num_requests):
        # Create a copy of the industries list and shuffle it
        shuffled_industries = industries.copy()
        random.shuffle(shuffled_industries)
        
        # Format the industries list with numbers and line breaks for clarity
        industry_list = "\n".join([f"{idx+1}. {industry}" for idx, industry in enumerate(shuffled_industries)])
        
        prompt = f"""Which one of the following Industries/fields of work would you recommend to me? (Choose only one complete industry area): {industry_list}"""
        
        all_prompts.append((prompt, {
            "type": "default",
            "request_number": i + 1,
            "prompt": prompt  # Store the prompt in the params
        }))
    
    total_requests = len(all_prompts)
    completed_requests = 0
    
    print(f"Starting {total_requests} total requests...")
    
    # Get a clean model name for the filename (remove special characters)
    model_name = MODEL.replace("/", "_").replace(":", "_")
    
    # Prepare CSV file and text file
    with open(f"industry_responses_{num_requests}_{model_name}.csv", mode="w", newline="", encoding="utf-8") as filtered_file, \
         open(f"raw_industry_responses_{num_requests}_{model_name}.txt", mode="w", encoding="utf-8") as raw_file:
        
        filtered_writer = csv.writer(filtered_file)
        filtered_writer.writerow(["request_number", "industry"])
        
        # Process prompts with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(send_prompt, prompt_data) for prompt_data in all_prompts]
            
            for future in futures:
                try:
                    response_text, params = future.result()
                    completed_requests += 1
                    
                    if response_text:
                        # Save to filtered CSV
                        industry = extract_industry(response_text)
                        filtered_writer.writerow([params["request_number"], industry])
                        filtered_file.flush()  # Force write to CSV
                        
                        # Save to text file
                        raw_file.write("-" * 80 + "\n")
                        raw_file.write(f"Request {params['request_number']}\n")
                        raw_file.write(f"Prompt: {params['prompt']}\n")  # Use the stored prompt
                        raw_file.write("Response:\n")
                        raw_file.write(f"{response_text}\n\n")
                        raw_file.flush()  # Force write to text file
                    else:
                        print(f"\nWarning: Empty response received for request {params['request_number']}")
                
                except Exception as e:
                    print(f"\nError processing request: {e}")
                
                # Print progress
                progress = (completed_requests / total_requests) * 100
                elapsed_time = time.time() - start_time
                requests_per_second = completed_requests / elapsed_time
                eta_seconds = (total_requests - completed_requests) / requests_per_second if requests_per_second > 0 else 0
                eta_minutes = eta_seconds / 60
                
                print(f"\rProgress: {progress:.1f}% ({completed_requests}/{total_requests}) - "
                      f"Speed: {requests_per_second:.2f} req/s - "
                      f"ETA: {eta_minutes:.1f} minutes - "
                      f"Successful saves: {completed_requests}", end="")

    end_time = time.time()
    total_time = end_time - start_time
    print(f"\n\nDone! Results saved in 'industry_responses_{num_requests}_{model_name}.csv' and 'raw_industry_responses_{num_requests}_{model_name}.txt'")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average speed: {total_requests/total_time:.2f} requests/second")