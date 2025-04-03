import requests
import json
import hashlib
import time
import os

# API Details
url_pre = "https://ap-east-1.tensorart.cloud"
api_key = "38dbb245-327b-485c-bfdf-63ae966edb73"  # Replace with your actual API key

# API Endpoints
url_job = "/v1/jobs"
url_resource = "/v1/resource"
url_workflow = "/v1/workflows"

# Headers for API Key Authentication
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

def ensure_output_folder():
    """Ensure that the 'outputs' folder exists."""
    if not os.path.exists("outputs"):
        os.makedirs("outputs")

def get_job_result(job_id):
    """Poll the API for job completion status."""
    while True:
        time.sleep(1)
        response = requests.get(f"{url_pre}{url_job}/{job_id}", headers=HEADERS)
        job_response = response.json()
        if 'job' in job_response:
            job_dict = job_response['job']
            job_status = job_dict.get('status')
            print("Job status:")
            print(job_dict)
            if job_status in ['SUCCESS', 'FAILED']:
                if job_status == 'SUCCESS':
                    image_url = job_dict['successInfo']['images'][0]['url']
                    print(f"Image URL: {image_url}")
                    print("Image generation successful.")
                    save_image(image_url)
                else:
                    print("Image generation failed.")
                break

def save_image(image_url):
    """Download and save the generated image."""
    ensure_output_folder()
    response = requests.get(image_url)
    if response.status_code == 200:
        image_path = os.path.join("outputs", f"{hashlib.md5(image_url.encode()).hexdigest()}.png")
        with open(image_path, "wb") as img_file:
            img_file.write(response.content)
        print(f"Image saved to {image_path}")
    else:
        print("Error downloading image.")

def upload_img(img_path):
    """Upload an image and return the resource ID."""
    print(f"Uploading image: {img_path}")
    data = {"expireSec": 3600}
    response = requests.post(f"{url_pre}{url_resource}/image", json=data, headers=HEADERS)
    print("Upload response:")
    print(response.text)
    response_data = response.json()
    resource_id = response_data['resourceId']
    put_url = response_data['putUrl']
    headers = response_data['headers']
    
    with open(img_path, 'rb') as f:
        res = f.read()
        upload_response = requests.put(put_url, data=res, headers=headers)
        print("PUT response:")
        print(upload_response.text)
    
    return resource_id

def workflow_template_job():
    """
    Submit a job using the predefined workflow template with template ID 688362427502551075.
    
    The payload includes:
      - Node "12" (LoadImage): "image" -> uploaded image resource ID.
      - Node "25" (SDXL Prompt Styler): "style", "text_positive", "text_negative".
      - Node "18" (IPAdapter FaceID): "weight" -> "0.8".
      - Node "3" (KSampler): "seed", "cfg", "steps", "sampler_name", "scheduler".
          (Do not override the "model" field so that the pointer remains intact.)
      - Node "5" (Empty Latent Image): "width", "height".
      - Node "4" (Load Checkpoint): "ckpt_name".
      - Node "38" (LoraLoaderModelOnly): "lora_name", "strength_model", "tams_lora_name".
      - And include "params": {"dummy": "dummy"} to ensure params is not null.
    """
    # Get user inputs
    img_path = input("Enter the path to your image file: ")
    positive_prompt = input("Enter the prompt for the image: ")
    style_value = input("Enter the style for the image (default: sai-line art): ")
    if not style_value:
        style_value = "sai-line art"
    
    # Fixed negative prompt value
    negative_prompt = (
        "lowres, bad hands, text, error, missing fingers, extra digit, fewer digits, "
        "cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, "
        "watermark, username, blurry, patreon logo, artist name, sexual content, adult, nuidity"
    )
    
    # Upload the image and get its resource ID
    resource_id = upload_img(img_path)
    
    # Build the payload with all required field attributes.
    data = {
        "request_id": hashlib.md5(str(int(time.time())).encode()).hexdigest(),
        "templateId": "688362427502551075",  # Template URL: https://tensor.art/template/688362427502551075
        "fields": {
            "fieldAttrs": [
                # Node 12: LoadImage (FACE)
                {"nodeId": "12", "fieldName": "image", "fieldValue": resource_id},
                # Node 25: SDXL Prompt Styler
                {"nodeId": "25", "fieldName": "style", "fieldValue": style_value},
                {"nodeId": "25", "fieldName": "text_positive", "fieldValue": positive_prompt},
                {"nodeId": "25", "fieldName": "text_negative", "fieldValue": negative_prompt},
                # Node 18: IPAdapter FaceID
                {"nodeId": "18", "fieldName": "weight", "fieldValue": "0.8"},
                # Node 3: KSampler (do not override the "model" pointer)
                {"nodeId": "3", "fieldName": "seed", "fieldValue": "161098661698898"},
                {"nodeId": "3", "fieldName": "cfg", "fieldValue": "2"},
                {"nodeId": "3", "fieldName": "steps", "fieldValue": "20"},
                {"nodeId": "3", "fieldName": "sampler_name", "fieldValue": "dpmpp_sde"},
                {"nodeId": "3", "fieldName": "scheduler", "fieldValue": "karras"},
                # {"nodeId": "3", "fieldName": "model", "fieldValue": "676746065682318967"},
                # Node 5: Empty Latent Image
                {"nodeId": "5", "fieldName": "width", "fieldValue": "1024"},
                {"nodeId": "5", "fieldName": "height", "fieldValue": "1024"},
                # Node 4: Load Checkpoint
                {"nodeId": "4", "fieldName": "ckpt_name", "fieldValue": "676746065682318967"},
                # Node 38: LoraLoaderModelOnly
                {"nodeId": "38", "fieldName": "lora_name", "fieldValue": "681174344216573550"},
                {"nodeId": "38", "fieldName": "strength_model", "fieldValue": "0.6"},
                {"nodeId": "38", "fieldName": "tams_lora_name", "fieldValue": "IP_adapter_face_id -  SDXL"}
            ]
        },
    }
    
    # Submit the job using the workflow template endpoint.
    response = requests.post(f"{url_pre}{url_job}/workflow/template", json=data, headers=HEADERS)
    print("Template job submission response:")
    print(response.text)
    response_data = response.json()
    
    if 'job' in response_data:
        job_dict = response_data['job']
        job_id = job_dict.get('id')
        job_status = job_dict.get('status')
        print(f"Workflow Job ID: {job_id}, Status: {job_status}")
        get_job_result(job_id)
    else:
        print("Failed to create workflow job:", response_data)

if __name__ == '__main__':
    workflow_template_job()
