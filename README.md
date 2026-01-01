# TEX Transformer: Automated LaTeX Transcription

A Python pipeline converting handwritten notes in PDF format into valid, formatted LaTeX documents. Currently suitable for math homework transcriptions of one page.

Current Version: **0.1.1**

## 💬 Features

This pipeline combines `marker-pdf` for layout analysis with Mistral's VLM for superior handwriting recognition. A modular Python architecture orchestrates the process, featuring robust post-processing to ensure valid LaTeX syntax (e.g., `\mathbb{N}`), strict list formatting, and accurate math delimiters.

## 🔎 Installation

1.  **Clone the repository**.
    ```bash
    git clone https://github.com/nathanleung/tex_transformer.git
    cd tex_transformer
    ```

2.  **Create the environment**:
    ```bash
    conda env create -f textenv.yml
    conda activate textenv
    ```

3.  **Setup Configuration**:
    Create a `.env` file in the root directory:
    ```bash
    MISTRAL_API_KEY=your_actual_api_key_here
    ```

4. **Standard Run**:
    Run the pipeline on your target PDF. The script handles OCR, Parsing, and Generation automatically.
    ```bash
    python main.py data/sample_1.pdf
    ```
    Output will be saved to `results/sample_1.pdf`.
