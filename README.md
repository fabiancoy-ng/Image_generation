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
    --prompt "A futuristic city with flying cars at sunset" 
```

Set the API Key as an environment variable:
```bash
GOOGLE_API_KEY=<API_KEY>
PROJECT_ID=project_ID
LOCATION=us-central1
```

### Arguments

-   `--prompt`: The text description of the image.

## Troubleshooting

-   **API Key Error**: Ensure your API key is valid and has the necessary permissions (Vertex AI API).
-   **SSL Errors during install**: Use the trusted host flags with pip.
