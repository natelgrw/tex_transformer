import os
from ocr_lib import pdf_to_processed_images

def verify():
    pdf_path = "data/sample_1.pdf"
    if not os.path.exists(pdf_path):
        print("Sample PDF not found.")
        return

    print("Processing images...")
    processed_images = pdf_to_processed_images(pdf_path)
    
    if processed_images:
        output_path = "results/verified_frame_0.jpg"
        if not os.path.exists("results"):
            os.makedirs("results")
            
        processed_images[0].save(output_path)
        print(f"Saved processed image to {output_path}")
    else:
        print("No images processed.")

if __name__ == "__main__":
    verify()
