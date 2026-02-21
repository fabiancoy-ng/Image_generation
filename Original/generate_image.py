#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
def generate_image(
    api_key: str,
    prompt: str,
    output_file: str = "generated_image.png",
    model_name: str = "imagen-4.0-generate-001",
    project_id: str = None,
    location: str = None,
) -> str | None:
    """Generates an image using Google GenAI and saves it to disk.

    Args:
        api_key: Google Cloud API key.
        prompt: Text prompt for image generation.
        output_file: Destination path for the generated image.
        model_name: Imagen model version to use.
        project_id: Optional GCP project ID (enables Vertex AI backend).
        location: Optional GCP region (used with project_id for Vertex AI).

    Returns:
        The path to the saved image on success, or None on failure.
    """
    print("Initializing GenAI Client...")

    # Prioritize API key auth; fall back to Vertex AI (service-account) only
    # when no API key is provided.
    if api_key:
        print("Using API key authentication.")
        client_kwargs = {"api_key": api_key}
    elif project_id and location:
        print(f"Using Vertex AI backend with project='{project_id}' and location='{location}'")
        client_kwargs = {
            "vertexai": True,
            "project": project_id,
            "location": location,
        }
    else:
        print("Error: No valid authentication method available.")
        return None

    try:
        client = genai.Client(**client_kwargs)
    except Exception as e:
        print(f"Error initializing client: {e}")
        return None

    print(f"Generating image with model '{model_name}' for prompt: '{prompt}'...")
    try:
        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="BLOCK_LOW_AND_ABOVE",
            person_generation="ALLOW_ADULT",
        )

        response = client.models.generate_images(
            model=model_name,
            prompt=prompt,
            config=config,
        )

        if not response.generated_images:
            print("No images were generated (the prompt may have been filtered).")
            return None

        image_bytes = response.generated_images[0].image.image_bytes

        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(output_file, "wb") as f:
            f.write(image_bytes)

        print(f"Image saved to {output_file}")
        return output_file

    except Exception as e:
        print(f"Error generating image: {e}")
        if hasattr(e, "message"):
            print(f"Detail: {e.message}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate an image using Google GenAI."
    )
    parser.add_argument(
        "--api_key",
        help="Google Cloud API Key (or set GOOGLE_API_KEY env var)",
    )
    parser.add_argument(
        "--project_id",
        help="Google Cloud Project ID (enables Vertex AI backend, overrides .env)",
    )
    parser.add_argument(
        "--location",
        help="Google Cloud Region (overrides .env, default: us-central1)",
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Text prompt for image generation",
    )
    parser.add_argument(
        "--output",
        default="generated_image.png",
        help="Output filename (default: generated_image.png)",
    )
    parser.add_argument(
        "--model",
        default="imagen-4.0-generate-001",
        help="Model version to use (default: imagen-4.0-generate-001)",
    )

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    project_id = args.project_id or os.environ.get("PROJECT_ID")
    location = args.location or os.environ.get("LOCATION") or "us-central1"

    if not api_key and not (project_id and location):
        print(
            "Error: Provide an API key (--api_key / GOOGLE_API_KEY env var) "
            "or a project_id + location for Vertex AI auth."
        )
        sys.exit(1)

    result = generate_image(
        api_key=api_key,
        prompt=args.prompt,
        output_file=args.output,
        model_name=args.model,
        project_id=project_id,
        location=location,
    )

    if result is None:
        sys.exit(1)
