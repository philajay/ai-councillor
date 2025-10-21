import google as genai
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def extract_data_from_urls(urls_and_tags):
    """
    Downloads content from URLs and extracts data using a generative AI model.

    Args:
        urls_and_tags: A list of dictionaries, where each dictionary contains a 'url' and a 'tag'.

    Returns:
        A list of dictionaries, where each dictionary contains the original URL, the tag, and the extracted data.
    """
    # In a real application, you would get the API key from a secure source.
    # For this example, we'll assume it's set as an environment variable.
    # genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    
    # For this example, we'll use a placeholder for the generative model
    # model = genai.GenerativeModel('gemini-pro')

    downloaded_data = []

    for item in urls_and_tags:
        url = item.get("url")
        tag = item.get("tag")

        if not url or not tag:
            logging.warning(f"Skipping item due to missing 'url' or 'tag': {item}")
            continue

        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            content = response.content  # Use .content for raw bytes (images, PDFs)
            mime_type = response.headers.get('Content-Type')

            downloaded_data.append({
                "content": content,
                "mime_type": mime_type
            })


        

        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading content from {url}: {e}")
            downloaded_data.append({
                "url": url,
                "tag": tag,
                "data": None,
                "error": str(e),
                "mime_type": None
            })

    # This is where you would use the generative AI model to extract data.
            # For this example, we'll just return a placeholder.
    from google import genai
    from google.genai import types
    import json
    client = genai.Client()
    

    prompt = """From the attached documents return the following json:
{
"Name": <Name of teh person>,
"DOB": <DOB>,
"SEX": <>,
"Address": <>,
"Zipcode": <>,
"State" :<>
}
"""
    l = [prompt]
    for d in downloaded_data:
        l.append(types.Part.from_bytes(
            data=d["content"],
            mime_type= d["mime_type"]
        ) )


    response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=l,
            config={
                "response_mime_type":"application/json"
            }
        )
    response = json.loads(response.text)
    return response

if __name__ == '__main__':
    # Example usage
    sample_data = [
        {"url": "https://storage.googleapis.com/councillorautomation.firebasestorage.app/Screenshot%202025-10-21%20at%208.21.53%E2%80%AFPM.png", "tag": "title"},
        {"url": "https://storage.googleapis.com/councillorautomation.firebasestorage.app/Screenshot%202025-10-21%20at%208.22.01%E2%80%AFPM.png", "tag": "h1"}
    ]
    
    results = extract_data_from_urls(sample_data)
    
    for result in results:
        print(result)
