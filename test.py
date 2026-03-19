def call_huggingface_api(prompt, max_length=500):
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_length": max_length,
            "temperature": 0.7,
            "top_p": 0.95,
            "do_sample": True
        },
        "model": "codellama/CodeLlama-7b-hf"  # specify model here
    }

    try:
        response = requests.post("https://router.huggingface.co", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # Extract generated text
        if isinstance(result, list) and len(result) > 0:
            generated_text = result[0].get('generated_text', '')
            return generated_text.replace(prompt, '').strip()
        elif isinstance(result, dict):
            return result.get('generated_text', '').strip()
        else:
            return "Error: Unexpected response format"

    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return get_demo_code(prompt)