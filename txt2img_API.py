import requests
import json
import hashlib
import time
import os

# Base URL for TensorArt API
url_pre = "https://ap-east-1.tensorart.cloud"

# Your API key (replace with your actual API key)
API_KEY = "38dbb245-327b-485c-bfdf-63ae966edb73"

# Endpoints
url_job = "/v1/jobs"

def ensure_output_folder():
    """Ensure that the 'outputs' folder exists in the root directory."""
    if not os.path.exists("outputs"):
        os.makedirs("outputs")

def text2img(positive_prompt):
    txt2img_data = {
        "request_id": hashlib.md5(str(int(time.time())).encode()).hexdigest(),
        "stages": [
            {
                "type": "INPUT_INITIALIZE",
                "inputInitialize": {
                    "seed": -1,
                    "count": 1
                }
            },
            {
                "type": "DIFFUSION",
                "diffusion": {
                    "width": 512,
                    "height": 512,
                    "prompts": [
                        {
                            "text": positive_prompt
                        }
                    ],
                    "sampler": "DPM++ 2M Karras",
                    "sdVae": "Automatic",
                    "steps": 15,
                    "sd_model": "600423083519508503",
                    "clip_skip": 2,
                    "cfg_scale": 7
                }
            }
        ]
    }

    response_data = create_job(txt2img_data)
    if 'job' in response_data:
        job_dict = response_data['job']
        job_id = job_dict.get('id')
        job_status = job_dict.get('status')
        print(f"Job ID: {job_id}, Status: {job_status}")
        get_job_result(job_id)

def get_job_result(job_id):
    while True:
        time.sleep(1)
        response = requests.get(
            f"{url_pre}{url_job}/{job_id}",
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f"Bearer {API_KEY}"
            }
        )
        get_job_response_data = response.json()
        if 'job' in get_job_response_data:
            job_dict = get_job_response_data['job']
            job_status = job_dict.get('status')
            if job_status == 'SUCCESS':
                image_url = job_dict['successInfo']['images'][0]['url']
                print(f"Image URL: {image_url}")
                print("Image generation successful.")
                save_image(image_url)
                break
            elif job_status == 'FAILED':
                print("Image generation failed.")
                break
            else:
                print(f"Job status: {job_status}")

def save_image(image_url):
    ensure_output_folder()
    response = requests.get(image_url)
    if response.status_code == 200:
        image_path = os.path.join("outputs", f"{hashlib.md5(image_url.encode()).hexdigest()}.png")
        with open(image_path, "wb") as img_file:
            img_file.write(response.content)
        print(f"Image saved to {image_path}")
    else:
        print("Error downloading image.")

def create_job(data):
    body = json.dumps(data)
    response = requests.post(
        f"{url_pre}{url_job}",
        json=data,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f"Bearer {API_KEY}"
        }
    )
    print(response.text)
    return response.json()

if __name__ == '__main__':
    positive_prompt = input("Enter the prompt for the image: ")
    text2img(positive_prompt)
