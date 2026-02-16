# Google Vertex AI Image Generator (API Key)

This project provides a Python script to generate images using Google Cloud Vertex AI (Imagen) via the `google-genai` library with an **API Key**.

## Prerequisites

1.  **Google Cloud Project**: A project with Vertex AI API enabled.
2.  **API Key**: An API key from Google Cloud Console with access to Vertex AI.

## Setup

1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    (If you have SSL errors, try: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`)

## Usage

Run the script with your API Key and other parameters:

```bash
python generate_image.py \
    --api_key "YOUR_API_KEY" \
    --project_id "YOUR_PROJECT_ID" \
    --location "us-central1" \
    --prompt "A futuristic city with flying cars at sunset" \
    --output "city.png"
```

Alternatively, set the API Key as an environment variable:
```bash
export GOOGLE_API_KEY="YOUR_API_KEY"
python generate_image.py \
    --project_id "YOUR_PROJECT_ID" \
    --prompt "A futuristic city with flying cars at sunset"
```

### Arguments

-   `--prompt`: The text description of the image.

## Troubleshooting

-   **API Key Error**: Ensure your API key is valid and has the necessary permissions (Vertex AI API).
-   **SSL Errors during install**: Use the trusted host flags with pip.
