
import os
import subprocess
import jinja2

class LaTeXGenerator:
    """
    Converts a structured JSON object into a compiled PDF homework document using a Jinja2 template.
    """
    
    LATEX_TEMPLATE = r"""
\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath, amssymb, amsthm}
\usepackage{indentfirst}

% Custom Commands
\newcommand{\N}{\mathbb{N}}

% Metadata
\title{Math Homework}
\author{John Doe}
\date{12/23/2025}

\begin{document}
\maketitle

((% for problem in problems %))
\section*{Problem ((( problem.problem_id )))}

((% if problem.content %))
((( problem.content )))
((% endif %))

((% for part in problem.parts %))
\subsection*{((( part.part_id ))))}

((( part.content )))

((% for subpart in part.subparts %))
\subsubsection*{((( subpart.subpart_id ))))}
((( subpart.content )))
((% endfor %))

((% endfor %))
((% endfor %))

\end{document}
"""

    def __init__(self):
        # Configure Jinja2 with custom delimiters to avoid LaTeX conflicts
        self.env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            block_start_string='((%',
            block_end_string='%))',
            variable_start_string='(((',
            variable_end_string=')))',
            comment_start_string='((#',
            comment_end_string='#))'
        )
        self.template = self.env.from_string(self.LATEX_TEMPLATE)

    def generate_tex(self, data):
        """
        Renders the LaTeX string from JSON data.
        """
        # Data passed directly: {"problems": [...]}
        return self.template.render(**data)

    def compile_pdf(self, data, output_pdf_path):
        """
        Compiles the JSON data into a PDF.
        Returns message string.
        """
        # 1. Pre-process data to handle custom list formatting (hanging indents for '>')
        self._process_lists(data)

        # 2. Generate TeX
        tex_content = self.generate_tex(data)
        
        # 3. Prepare paths
        output_dir = os.path.dirname(os.path.abspath(output_pdf_path))
        base_name = os.path.splitext(os.path.basename(output_pdf_path))[0]
        tex_file_path = os.path.join(output_dir, f"{base_name}.tex")
        
        # 4. Write TeX file
        with open(tex_file_path, "w", encoding="utf-8") as f:
            f.write(tex_content)
            
        # 5. Compile
        try:
            # Try using tectonic first (modern, self-contained engine)
            # Command: tectonic file.tex
            cmd = ["tectonic", tex_file_path]
            
            # Using subprocess.run
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Fallback check or error reporting
                print("Tectonic Compilation Failed:")
                print(result.stdout)
                print(result.stderr)
                return f"Error compiling with Tectonic. Check logs. stderr: {result.stderr[:200]}..."
            
            # Tectonic produces PDF in the same dir by default
            # Check if created
            if os.path.exists(output_pdf_path):
                 return f"Success! PDF saved to {output_pdf_path}"
            else:
                 return "Error: Tectonic ran but PDF not found."
            
        except FileNotFoundError:
             return "Error: 'tectonic' compiler not found in PATH."
        except Exception as e:
            return f"Exception during compilation: {e}"

    def _process_lists(self, data):
        """
        Traverse the data structure and transform '> ' lines into properly indented LaTeX itemize blocks.
        """
        if "problems" not in data:
            return

        for problem in data["problems"]:
             # Process Problem Content
             if "content" in problem and problem["content"]:
                 problem["content"] = self._transform_bullets_to_latex(problem["content"])
                 
             if "parts" in problem:
                 for part in problem["parts"]:
                     # Process Part Content
                     if "content" in part and part["content"]:
                         part["content"] = self._transform_bullets_to_latex(part["content"])
                     
                     # Process Subparts
                     if "subparts" in part:
                         for subpart in part["subparts"]:
                             if "content" in subpart and subpart["content"]:
                                 subpart["content"] = self._transform_bullets_to_latex(subpart["content"])

    def _transform_bullets_to_latex(self, text):
        r"""
        Converts lines starting with '> ' into \begin{itemize}\item[>] ... \end{itemize}
        Handles grouping if lines are consecutive, or separate lists if separated.
        """
        lines = text.split('\n')
        new_lines = []
        in_list = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(">"):
                # Clean content: remove '> ' or '>'
                content = stripped[1:].strip()
                
                if not in_list:
                    new_lines.append(r"\begin{itemize}")
                    in_list = True
                
                # Use [>] as label
                new_lines.append(r"\item[>] " + content)
            else:
                if in_list:
                    new_lines.append(r"\end{itemize}")
                    in_list = False
                
                new_lines.append(line)
        
        # Close any open list at end
        if in_list:
             new_lines.append(r"\end{itemize}")
             
        return "\n".join(new_lines)
