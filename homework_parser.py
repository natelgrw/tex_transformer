
import re
import json

class HomeworkParser:
    """
    Parses a Markdown string containing structured math homework (Problem > Part > Content)
    into a hierarchical JSON object.
    
    Structure Mapping:
    - # Problem X  -> problems entry
    - ## a)        -> parts entry
    - ### i)       -> part content (or subpart if schema allows, currently treating as content)
    - Content      -> raw string
    """
    
    def __init__(self):
        # Regex Patterns
        # Matches: "# Problem 1", "## Problem 1", or just "Problem 1" (robustness)
        self.problem_pattern = re.compile(r'^(?:#|##)?\s*Problem\s+(\d+)', re.IGNORECASE)
        
        # Matches: "## a)" or "## b)" -- STRICTLY ## for Parts
        self.part_pattern = re.compile(r'^##\s*([a-z]\))', re.IGNORECASE)
        
        # Matches: "### i)", "### ii)", etc. -- STRICTLY ### for Subparts
        self.subpart_pattern = re.compile(r'^###\s*([ivx]+\))', re.IGNORECASE)
        
        # Proof Markers
        self.proof_start = r'\begin{proof}'
        self.proof_end = r'\end{proof}'
        
        # Internal State
        self.problems = []
        self.current_problem = None # Dict
        self.current_part = None    # Dict
        self.current_subpart = None # Dict
        
    def parse(self, markdown_string):
        """
        Main entry point. Iterates line-by-line using a state machine.
        """
        lines = markdown_string.split('\n')
        
        for line in lines:
            line = line.rstrip() 
            self._process_line(line)
            
        # Final cleanup after loop
        self._finalize_current_blocks()
        
    def to_json(self):
        """
        Exports the parsed structure to JSON.
        """
        output = {
            "problems": self.problems
        }
        return json.dumps(output, indent=4)
        
    def _process_line(self, line):
        clean_line = line.strip()
        
        # 1. Check for New Problem Header
        problem_match = self.problem_pattern.match(clean_line)
        if problem_match:
            self._finalize_current_blocks() # Close everything
            
            problem_id = problem_match.group(1)
            self.current_problem = {
                "problem_id": problem_id,
                "content": "", # For "headless" problems (no parts)
                "parts": [],
                "_temp_lines": [] 
            }
            self.problems.append(self.current_problem)
            return

        # 2. Check for New Part Header
        # Only valid if we have an active problem
        part_match = self.part_pattern.match(clean_line)
        if part_match and self.current_problem is not None:
            self._finalize_problem_content() # Finish problem content
            self._finalize_current_part_and_subparts() # Close existing part & subparts
            
            part_id = part_match.group(1).replace(')', '')
            
            self.current_part = {
                "part_id": part_id,
                "content": "",
                "subparts": [],
                "_temp_lines": [] # Buffer for content
            }
            self.current_problem["parts"].append(self.current_part)
            return
            
        # 3. Check for Subpart Header (### i))
        if self.current_part is not None:
             subpart_match = self.subpart_pattern.match(clean_line)
             if subpart_match:
                self._finalize_current_subpart() # Close existing subpart
                
                subpart_id = subpart_match.group(1).replace(')', '')
                
                self.current_subpart = {
                    "subpart_id": subpart_id,
                    "content": "",
                    "_temp_lines": []
                }
                self.current_part["subparts"].append(self.current_subpart)
                return

        # 4. Handle Content Logic
        # Priority: Subpart > Part > Problem
        if self.current_subpart is not None:
            self.current_subpart["_temp_lines"].append(line)
        elif self.current_part is not None:
            self.current_part["_temp_lines"].append(line)
        elif self.current_problem is not None:
            self.current_problem["_temp_lines"].append(line)
            
    def _finalize_current_blocks(self):
        self._finalize_problem_content()
        self._finalize_current_part_and_subparts()
        self.current_problem = None
        
    def _finalize_current_part_and_subparts(self):
        self._finalize_current_subpart() # Close subpart first
        self._finalize_current_part()    # Then close part
        
    def _finalize_current_subpart(self):
        if self.current_subpart:
            content_lines = self.current_subpart["_temp_lines"]
            self.current_subpart["content"] = self._clean_content("\n".join(content_lines))
            del self.current_subpart["_temp_lines"]
            self.current_subpart = None

    def _finalize_current_part(self):
        if self.current_part:
            content_lines = self.current_part["_temp_lines"]
            self.current_part["content"] = self._clean_content("\n".join(content_lines))
            del self.current_part["_temp_lines"]
            self.current_part = None

    def _finalize_problem_content(self):
        if self.current_problem:
            # Only process if we haven't already moved past problem content?
            # Actually, _temp_lines stays with problem until finalized?
            # But wait, once we are in a part, we shouldn't add to problem content.
            # My logic in _process_line: 'elif self.current_problem'. So once part is active, problem content stops.
            # So we can finalize problem content whenever we switch/close problem, 
            # OR we can just finalize it at the end. Use a check to avoid double processing.
            if "_temp_lines" in self.current_problem:
                 content_lines = self.current_problem["_temp_lines"]
                 # Append to existing content or set? usually sequential.
                 if content_lines:
                     new_content = self._clean_content("\n".join(content_lines))
                     if self.current_problem["content"]:
                         self.current_problem["content"] += "\n" + new_content
                     else:
                         self.current_problem["content"] = new_content
                     
                     # Clear lines so we don't re-add
                     self.current_problem["_temp_lines"] = []
            
    def _clean_content(self, text):
        return text.strip()
