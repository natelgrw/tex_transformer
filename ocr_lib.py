import os
import io
import base64
import re
from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_path

try:
    from mistralai import Mistral # New SDK client
except ImportError:
    Mistral = None

import numpy as np
try:
    import cv2
except ImportError:
    cv2 = None

def preprocess_image(image):
    """
    The Enhancer: Prepare image for VLM using OpenCV.
    - Convert to Grayscale
    - Apply Adaptive Thresholding (Illumination Correction)
    - Denoise
    """
    if cv2 is None:
        # Fallback if cv2 missing
        return image.convert('L').filter(ImageFilter.SHARPEN)

    img_np = np.array(image)
    if len(img_np.shape) == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np

    # 1. Denoising
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Illumination Correction / Adaptive Thresholding
    thresh = cv2.adaptiveThreshold(
        blurred, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        15, 
        10
    )
    return Image.fromarray(thresh)

def pdf_to_processed_images(pdf_path, dpi=300):
    """
    Convert PDF to 300 DPI images and preprocess them.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
    print(f"Converting PDF {pdf_path} to images at {dpi} DPI...")
    raw_images = convert_from_path(pdf_path, dpi=dpi)
    
    processed_images = []
    for img in raw_images:
        processed_images.append(preprocess_image(img))
        
    return processed_images

def run_vision_ocr(pdf_path, api_key=None):
    """
    The Transcriber: Run Vision-Language Model on processed images.
    """
    if not api_key:
        api_key = os.environ.get("MISTRAL_API_KEY")
    
    if not api_key:
        raise ValueError("Mistral API Key required for VLM OCR. Set MISTRAL_API_KEY env var.")
        
    if not Mistral:
        raise ImportError("mistralai library not installed.")

    client = Mistral(api_key=api_key)
    
    # Get processed images
    images = pdf_to_processed_images(pdf_path)
    
    full_transcript = []
    
    # System Instruction for the VLM
    system_prompt = (
        "Transcribe this handwritten math homework into Markdown.\n"
        "STRICTLY FOLLOW this structure and these rules:\n\n"
        "1. **Structure Hierarchy**:\n"
        "   - Use '# Problem X' for main problems.\n"
        "   - Use '## a)', '## b)' for parts.\n"
        "   - Use '### i)', '### ii)' for subparts.\n"
        "   - DO NOT hallucinate headers (like '## Proof 7') unless clearly written.\n\n"
        "2. **Math Formatting (CRITICAL)**:\n"
        "   - ALL math MUST be in LaTeX delimiters: $...$ for inline, $$...$$ for display.\n"
        "   - NEVER output raw Unicode math symbols (e.g. use '\\mathbb{N}' NOT 'ℕ').\n\n"
        "3. **Bullet Points**:\n"
        "   - Use '> ' for bullet points (representing handwritten arrows/bullets).\n"
        "   - Leave 2 blank lines between bullet items.\n\n"
        "4. **Visual Recognition Rules (CRITICAL)**:\n"
        "   - **Subscripts**: $a_n$ is extremely common. Transcribe as $a_n$. (Avoid $an$ unless it is very clearly on the same baseline as 'a').\n"
        "   - **Definition (:=)**: If you see a colon followed by equals, you MUST write ':='.\n"
        "   - **Modulo (%)**: Literally transcribe as '%'. (e.g. $40 % 3 = 1$).\n"
        "   - **Q.E.D.**: If you see a square box, write '\\blacksquare'.\n\n"
        "5. **Formatting & Linearity (MANDATORY)**:\n"
        "   - **STRICT LINEARITY**: If multiple equations or steps appear together on the same line or in a tight cluster, you MUST MERGE them into a single line in Markdown. Use commas to separate them. Example: '$x^2-4=0, (x-2)(x+2)=0, x=2, -2$'.\n"
        "   - **NO BLOCK MATH**: Avoid using `$$ ... $$` for simple or medium steps. Stick to inline `$ ... $` to keep everything compact.\n"
        "   - **No Conversational Text**: Do not add 'End.', 'Done', or 'Solution'.\n\n"
        "6. **EXACT FORMAT EXAMPLE**:\n"
        "# Problem 1\n\n"
        "## a)\n"
        "Proof:\n\n"
        "> $a \\geq 0, b \\in \\mathbb{N}$\n\n\n"
        "> $0 \\in \\mathbb{N} \\implies a \\in \\mathbb{N}$ $\\blacksquare$\n\n"
        "## b)\n"
        "$x^2 - 2x - 8 = 0, (x-4)(x+2)=0, x=4, -2$"
    )

    for i, img in enumerate(images):
        print(f"Processing page {i+1} with Pixtral VLM...")
        
        # Encode image
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Construct Message
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": system_prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_base64}"}
                ]
            }
        ]
        
        try:
            chat_response = client.chat.complete(
                model="pixtral-12b-2409", 
                messages=messages,
                temperature=0.1 
            )
            content = chat_response.choices[0].message.content
            
            # --- Post-Processing Fixes ---
            # 1. Modulo/Percent Fix: Normalize escaping.
            # Convert any existing \% back to % temporarily, then escape all % to \%.
            # This handles both "%" -> "\%" and "\%" -> "\%".
            content = content.replace("\\%", "%").replace("%", "\\%")
            
            # 2. Definition Fix: ": =" -> ":=" (VLM common whitespace error)
            content = content.replace(": =", ":=")
            
            # Post-process: Strip markdown code fences if present
            if content.startswith("```"):
                lines = content.split('\n')
                # Remove first line if it's ```markdown or ```
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)

            # FORCE User Requirements:
            # 1. Replace standard bullets '- ' or '* ' with '> '
            # 2. Add extra newlines for detected bullets
            # Regex lookbehinds/aheads to find list items at start of line
            # Pattern: newline followed by - or * and space
            # We want to replace it with "\n\n\n> " to ensure the gap
            # Note: This is an aggressive replacement to satisfy the strict requirement.
            content = re.sub(r'(^|\n)([-*])\s+', r'\1\n\n> ', content)
            
            # FORCE Newline after Headers (e.g. "## a) Proof" -> "## a)\nProof")
            # Pattern: (##... ) (text) -> \1\n\2
            content = re.sub(r'^(#+\s+[a-zA-Z0-9]+\))\s+(.+)', r'\1\n\2', content, flags=re.MULTILINE)

            full_transcript.append(content)
        except Exception as e:
            print(f"Error processing page {i+1}: {e}")
            full_transcript.append(f"[Error deriving page {i+1}]")
            
    return "\n\n".join(full_transcript)
