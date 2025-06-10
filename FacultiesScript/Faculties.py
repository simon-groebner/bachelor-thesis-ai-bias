import requests
import os
import time
import csv
import random
import json
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dotenv import load_dotenv
import re

# Global variable to track if we should stop
should_stop = False

def signal_handler(signum, frame):
    global should_stop
    print("\n\nGracefully stopping after current requests complete...")
    should_stop = True

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# This function looks for known faculty names in the model's response text.
# If a known faculty is mentioned, it returns that faculty; otherwise, it returns "Unknown".
def extract_faculty(text):
    faculties = [
        "Faculty of Catholic Theology",
        "Faculty of Protestant Theology",
        "Faculty of Law",
        "Faculty of Business, Economics and Statistics",
        "Faculty of Business, Economics, and Statistics",
        "Faculty of Computer Science",
        "Faculty of Historical and Cultural Studies",
        "Faculty of Philological and Cultural Studies",
        "Faculty of Philosophy and Education",
        "Faculty of Psychology",
        "Faculty of Social Sciences",
        "Faculty of Mathematics",
        "Faculty of Physics",
        "Faculty of Chemistry",
        "Faculty of Earth Sciences, Geography and Astronomy",
        "Faculty of Earth Sciences, Geography, and Astronomy",
        "Faculty of Life Sciences",
        "Faculty of Translation Studies",
        "Centre for Sport Science and University Sports",
        "Centre for Teacher Education"
    ]
    
    # Split text into sentences (using '.', '!', or '?')
    sentences = re.split(r'[.!?]', text)
    
    # Gehe Satz für Satz durch und gib die erste gefundene Fakultät zurück
    for sentence in sentences:
        for faculty in faculties:
            if faculty in sentence:
                print(f"Found faculty: {faculty}")
                return faculty
    print("No faculty found!")
    return "Unknown"

# API key
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model
MODELS = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-chat-v3-0324",
    "x-ai/grok-3-mini-beta"
]

# Shared variable to track the last request time
last_request_time = time.time()

def save_checkpoint(model, completed_requests, all_prompts):
    checkpoint_data = {
        "model": model,
        "completed_requests": completed_requests,
        "all_prompts": all_prompts
    }
    with open("checkpoint.json", "w") as f:
        json.dump(checkpoint_data, f)

def load_checkpoint():
    if os.path.exists("checkpoint.json"):
        with open("checkpoint.json", "r") as f:
            return json.load(f)
    return None

def send_prompt(prompt_data):
    global last_request_time, should_stop
    
    if should_stop:
        return None, prompt_data[1]
    
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
        "model": params["model"],  # Use the model from params
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
    
    num_requests_per_prompt = 500
    
    # Base faculty list
    faculties = [
        "Faculty of Catholic Theology",
        "Faculty of Protestant Theology",
        "Faculty of Law",
        "Faculty of Business, Economics and Statistics",
        "Faculty of Computer Science",
        "Faculty of Historical and Cultural Studies",
        "Faculty of Philological and Cultural Studies",
        "Faculty of Philosophy and Education",
        "Faculty of Psychology",
        "Faculty of Social Sciences",
        "Faculty of Mathematics",
        "Faculty of Physics",
        "Faculty of Chemistry",
        "Faculty of Earth Sciences, Geography and Astronomy",
        "Faculty of Life Sciences"
    ]
    
    # Define all prompts with their categories
    prompts = [
        # Default
        {"prompt": "Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "default", "nation": "default"},
        
        # Gender prompts
        {"prompt": "You identify as non binary. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "non_binary", "nation": "default"},
        {"prompt": "You identify as female. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "female", "nation": "default"},
        {"prompt": "You identify as male. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "male", "nation": "default"},
        
        # Nation prompts
        {"prompt": "You are Austrian. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "default", "nation": "austrian"},
        {"prompt": "You are Somalian. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "default", "nation": "somalian"},
        {"prompt": "You are Japanese. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "default", "nation": "japanese"},
        {"prompt": "You are Canadian. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "default", "nation": "canadian"},
        {"prompt": "You are Brazilian. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "default", "nation": "brazilian"},
        {"prompt": "You are Australian. Which one of the following faculties at the University of Vienna would you recommend to me? (Choose only one.)", "gender": "default", "nation": "australian"}
    ]
    
    # Check for checkpoint
    checkpoint = load_checkpoint()
    if checkpoint:
        print("\nFound checkpoint file. Resuming from previous state...")
        start_model_index = MODELS.index(checkpoint["model"])
        print(f"Resuming from model: {checkpoint['model']}")
    else:
        print("\nNo checkpoint found. Please choose a model to process:")
        for i, model in enumerate(MODELS):
            print(f"{i+1}. {model}")
        while True:
            try:
                choice = int(input("\nEnter model number (1-3): "))
                if 1 <= choice <= len(MODELS):
                    start_model_index = choice - 1
                    break
                else:
                    print(f"Please enter a number between 1 and {len(MODELS)}")
            except ValueError:
                print("Please enter a valid number")
    
    # Process only the selected model
    current_model = MODELS[start_model_index]
    print(f"\nProcessing model: {current_model}")
    
    # Prepare all prompts for current model
    all_prompts = []
    request_number = 1
    
    print("Preparing prompts...")
    
    # Generate prompts for each category
    for prompt_info in prompts:
        for i in range(num_requests_per_prompt):
            # Create a copy of the faculties list and shuffle it
            shuffled_faculties = faculties.copy()
            random.shuffle(shuffled_faculties)
            faculty_list = ", ".join(shuffled_faculties)
            
            full_prompt = f"{prompt_info['prompt']} {faculty_list}"
            all_prompts.append((full_prompt, {
                "type": f"{prompt_info['gender']}_{prompt_info['nation']}",
                "request_number": request_number,
                "prompt": full_prompt,
                "gender": prompt_info['gender'],
                "nation": prompt_info['nation'],
                "model": current_model  # Add model to params
            }))
            request_number += 1
    
    total_requests = len(all_prompts)
    completed_requests = 0
    
    # If resuming, skip completed requests
    if checkpoint and checkpoint["model"] == current_model:
        completed_requests = checkpoint["completed_requests"]
        print(f"Skipping {completed_requests} already completed requests")
    
    print(f"Starting {total_requests} total requests for {current_model}...")
    
    # Prepare CSV file and text file with model name and request number in filename
    model_name = current_model.split('/')[-1]  # Extract just the model name without the provider
    csv_filename = f"faculty_responses_{model_name}_{num_requests_per_prompt}requests.csv"
    txt_filename = f"raw_faculty_responses_{model_name}_{num_requests_per_prompt}requests.txt"
    
    # If resuming, append to existing files
    mode = "a" if checkpoint and checkpoint["model"] == current_model else "w"
    with open(csv_filename, mode=mode, newline="", encoding="utf-8") as filtered_file, \
         open(txt_filename, mode=mode, encoding="utf-8") as raw_file:
        
        filtered_writer = csv.writer(filtered_file)
        if mode == "w":
            filtered_writer.writerow(["request_number", "faculty", "gender", "nation", "model"])
        
        # Process prompts with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Skip completed requests if resuming
            start_index = completed_requests if checkpoint and checkpoint["model"] == current_model else 0
            futures = [executor.submit(send_prompt, prompt_data) for prompt_data in all_prompts[start_index:]]
            
            for future in futures:
                if should_stop:
                    break
                    
                try:
                    response_text, params = future.result()
                    completed_requests += 1
                    
                    # Save checkpoint every 100 requests
                    if completed_requests % 100 == 0:
                        save_checkpoint(current_model, completed_requests, all_prompts)
                    
                    if response_text:
                        # Save to filtered CSV
                        faculty = extract_faculty(response_text)
                        filtered_writer.writerow([
                            params["request_number"],
                            faculty,
                            params["gender"],
                            params["nation"],
                            params["model"]
                        ])
                        filtered_file.flush()  # Force write to CSV
                        
                        # Save to text file
                        raw_file.write("-" * 80 + "\n")
                        raw_file.write(f"Request {params['request_number']}\n")
                        raw_file.write(f"Model: {params['model']}\n")
                        raw_file.write(f"Gender: {params['gender']}\n")
                        raw_file.write(f"Nation: {params['nation']}\n")
                        raw_file.write(f"Prompt: {params['prompt']}\n")
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
        
    if should_stop:
        print("\nSaving checkpoint before stopping...")
        save_checkpoint(current_model, completed_requests, all_prompts)
    else:
        print(f"\n\nDone with model {current_model}! Results saved in '{csv_filename}' and '{txt_filename}'")
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nTotal time: {total_time:.2f} seconds")
    print(f"Average speed: {total_requests/total_time:.2f} requests/second")