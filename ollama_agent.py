import ollama # Changed from anthropic
import os
import json
import sys
from pathlib import Path

# ANSI escape codes for colors
class Colors:
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    ENDC = '\033[0m'

class ToolDefinition:
    """
    A simple class to hold tool definition details.
    """
    def __init__(self, name, description, input_schema, function):
        self.name = name
        self.description = description
        self.input_schema = input_schema # This is the JSON schema for parameters
        self.function = function # The actual Python function to call

    def to_ollama_format(self):
        """Converts the tool definition to the format Ollama API expects."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema, # Directly use the schema here
            },
        }

# --- Tool Implementations (No changes needed here for Ollama) ---

def read_file_tool(input_data: dict) -> str:
    """
    Reads the content of a given relative file path.
    input_data: A dictionary, e.g., {"path": "file.txt"}
    Returns raw content string on success, or a JSON string with an error key on failure.
    """
    path_str = input_data.get("path")
    if not path_str:
        return json.dumps({"error": "Path is required."})
    
    try:
        file_path = Path(path_str).resolve()
        if not str(file_path).startswith(str(Path.cwd().resolve())):
             return json.dumps({"error": f"Access to path '{path_str}' is not allowed. Only paths within the current working directory are permitted."})

        if not file_path.is_file():
            return json.dumps({"error": f"File not found or is not a regular file: {path_str}"})
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return json.dumps({"error": f"Error reading file {path_str}: {str(e)}"})

def list_files_tool(input_data: dict) -> str:
    """
    Lists files and directories at a given path.
    If no path is provided, lists files in the current directory.
    input_data: A dictionary, e.g., {"path": "some_dir/"} or {}
    Returns a JSON string array on success, or a JSON string with an error key on failure.
    """
    path_str = input_data.get("path", ".")
    
    try:
        base_path = Path(path_str).resolve()
        if not str(base_path).startswith(str(Path.cwd().resolve())):
             return json.dumps({"error": f"Access to path '{path_str}' is not allowed. Only paths within the current working directory are permitted."})

        if not base_path.exists():
            return json.dumps({"error": f"Path not found: {path_str}"})

        files_and_dirs = []
        for item in base_path.iterdir():
            name = item.name
            if item.is_dir():
                files_and_dirs.append(name + "/")
            else:
                files_and_dirs.append(name)
        
        return json.dumps(files_and_dirs)
    except Exception as e:
        return json.dumps({"error": f"Error listing files in {path_str}: {str(e)}"})

def _create_new_file(file_path_str: str, content: str) -> str:
    """Helper to create a new file and necessary directories."""
    try:
        p = Path(file_path_str).resolve()
        if not str(p).startswith(str(Path.cwd().resolve())):
             return json.dumps({"error": f"Access to path '{file_path_str}' is not allowed for creation. Only paths within the current working directory are permitted."})

        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created file {file_path_str}" # Success message
    except Exception as e:
        return json.dumps({"error": f"Failed to create file {file_path_str}: {str(e)}"})


def edit_file_tool(input_data: dict) -> str:
    """
    Edits a text file by replacing 'old_str' with 'new_str' or creates a new file.
    Returns "OK" or success message on success, or a JSON string with an error key on failure.
    """
    path_str = input_data.get("path")
    old_str = input_data.get("old_str")
    new_str = input_data.get("new_str")

    if path_str is None or new_str is None:
        return json.dumps({"error": "Invalid input: 'path' and 'new_str' are required."})
    
    if old_str is not None and old_str == new_str:
        return json.dumps({"error": "Invalid input: 'old_str' and 'new_str' must be different if 'old_str' is provided."})

    file_path = Path(path_str).resolve()
    if not str(file_path).startswith(str(Path.cwd().resolve())):
        return json.dumps({"error": f"Access to path '{path_str}' is not allowed. Only paths within the current working directory are permitted."})

    try:
        if not file_path.exists():
            if old_str == "" or old_str is None:
                return _create_new_file(path_str, new_str)
            else:
                return json.dumps({"error": f"File not found: {path_str}, and 'old_str' was provided, so not creating a new file."})
        
        if not file_path.is_file():
            return json.dumps({"error": f"Path exists but is not a file: {path_str}"})

        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        if old_str not in original_content:
            return json.dumps({"error": f"'old_str' not found in file {path_str}."})
        if old_str is None or old_str == "":
            modified_content = original_content + new_str
        else:
            modified_content = original_content.replace(old_str, new_str)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)
        
        return "OK"
    except Exception as e:
        return json.dumps({"error": f"Error editing file {path_str}: {str(e)}"})


# --- Tool Definitions (Schemas remain the same, functions are the same) ---
READ_FILE_DEFINITION = ToolDefinition(
    name="read_file",
    description="Read the contents of a given relative file path. Use this when you want to see what's inside a file. Do not use this with directory names.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The relative path of a file in the working directory."}
        },
        "required": ["path"],
    },
    function=read_file_tool,
)

LIST_FILES_DEFINITION = ToolDefinition(
    name="list_files",
    description="List files and directories at a given path. If no path is provided, lists files in the current directory. Returns a JSON string array.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Optional relative path to list files from. Defaults to current directory if not provided."}
        },
    },
    function=list_files_tool,
)

EDIT_FILE_DEFINITION = ToolDefinition(
    name="edit_file",
    description="Make edits to a text file. Replaces 'old_str' with 'new_str' in the given file. 'old_str' and 'new_str' MUST be different from each other. If the file specified with path doesn't exist AND 'old_str' is empty, it will be created with 'new_str' as content. If 'old_str' is provided, it must exist in the file. If 'old_str' is empty and file exists, 'new_str' will be appended to the end of the file." ,
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The path to the file."},
            "old_str": {"type": "string", "description": "Text to search for. If creating a new file, this should be empty. If provided, it must exist in the file."},
            "new_str": {"type": "string", "description": "Text to replace old_str with, or the content for a new file."}
        },
        "required": ["path", "new_str"],
    },
    function=edit_file_tool,
)


class Agent:
    def __init__(self, tools=None, model_name="llama3.1"):
        try:
            # Check if Ollama server is running and the model is available
            ollama.list() 
            # You might want to add a specific check for model_name if ollama.list() doesn't suffice
            print(f"{Colors.GREEN}Successfully connected to Ollama server.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}Error connecting to Ollama server: {e}{Colors.ENDC}")
            print(f"{Colors.RED}Please ensure the Ollama server is running and accessible.{Colors.ENDC}")
            sys.exit(1)
            
        self.tools = tools if tools else []
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.model_name = model_name
        print(f"{Colors.BLUE}Using Ollama model: {self.model_name}{Colors.ENDC}")
        print(f"{Colors.BLUE}Make sure '{self.model_name}' is pulled ('ollama pull {self.model_name}') and supports tool calling.{Colors.ENDC}")


    def get_user_message(self):
        try:
            return input(f"{Colors.BLUE}You{Colors.ENDC}: ")
        except EOFError:
            return None
        except KeyboardInterrupt:
            return None

    def run_inference(self, conversation_history):
        """Sends the conversation to Ollama and gets a response."""
        ollama_tools_spec = [tool.to_ollama_format() for tool in self.tools]
        
        try:
            # Using the module-level ollama.chat function as per the example
            response = ollama.chat(
                model=self.model_name,
                messages=conversation_history,
                tools=ollama_tools_spec if ollama_tools_spec else None,
                # stream=False # Default is False, which is what we want here
            )
            return response
        except Exception as e: # Catching generic Exception, ollama might have specific API errors
            print(f"{Colors.RED}Ollama API Error: {e}{Colors.ENDC}")
            return None

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """
        Executes a tool and returns its string result (success message or JSON error string).
        """
        if tool_name not in self.tool_map:
            error_msg = f"Tool '{tool_name}' not found by agent."
            print(f"{Colors.RED}Error: {error_msg}{Colors.ENDC}")
            return json.dumps({"error": error_msg})

        tool_to_execute = self.tool_map[tool_name]
        try:
            result_string = tool_to_execute.function(tool_input)
            return result_string
        except Exception as e:
            # This catch is a fallback if the tool function itself raises an unexpected error
            error_msg = f"Agent failed to execute tool {tool_name}: {str(e)}"
            print(f"{Colors.RED}Error executing tool {tool_name}: {e}{Colors.ENDC}")
            return json.dumps({"error": error_msg})

    def run(self):
        """Main loop for the agent."""
        conversation = []
        print(f"Chat with Ollama (model: {self.model_name}). Use 'ctrl-c' or 'ctrl-d' to quit.")

        needs_user_input = True
        while True:
            if needs_user_input:
                user_input = self.get_user_message()
                if user_input is None:
                    print(f"\n{Colors.YELLOW}Exiting chat.{Colors.ENDC}")
                    break
                if not user_input.strip():
                    continue
                conversation.append({"role": "user", "content": user_input})
            
            ollama_response = self.run_inference(conversation)
            if ollama_response is None: # API error likely
                needs_user_input = True 
                continue

            # The assistant's message, potentially including tool_calls
            assistant_turn_message = ollama_response['message']
            conversation.append(assistant_turn_message) # Add assistant's turn to history

            # Extract text content and tool calls from assistant's message
            assistant_text_content = assistant_turn_message.get('content')
            raw_tool_calls = assistant_turn_message.get('tool_calls') # This will be a list or None

            if assistant_text_content:
                print(f"{Colors.YELLOW}Assistant{Colors.ENDC}: {assistant_text_content.strip()}")

            if raw_tool_calls:
                needs_user_input = False # Process tools, then let Ollama respond
                
                tool_result_messages_for_ollama = []
                for tool_call_request in raw_tool_calls:
                    tool_name = tool_call_request['function']['name']
                    
                    # Arguments from Ollama are expected to be a dictionary directly
                    tool_arguments = tool_call_request['function']['arguments']

                    # Verify that tool_arguments is a dictionary
                    if not isinstance(tool_arguments, dict):
                        error_message = f"Tool arguments for '{tool_name}' are not in the expected dictionary format."
                        detailed_error_info = f"Received arguments: {tool_arguments}, type: {type(tool_arguments)}"
                        print(f"{Colors.RED}{error_message} {detailed_error_info}{Colors.ENDC}")
                        
                        tool_result_messages_for_ollama.append({
                            "role": "tool",
                            "content": json.dumps({
                                "error": error_message,
                                "received_arguments": str(tool_arguments) # Convert to string for JSON
                            })
                        })
                        continue # Skip to next tool call if any

                    tool_input_data = tool_arguments # Use the dictionary directly

                    print(f"{Colors.GREEN}tool_call{Colors.ENDC}: {tool_name}({json.dumps(tool_input_data)})") # For logging, json.dumps is fine
                    
                    # Execute the tool
                    result_string_content = self.execute_tool(tool_name, tool_input_data)
                    print(f"{Colors.GREEN}tool_result{Colors.ENDC}: {result_string_content}")
                    
                    # Prepare tool result message for Ollama
                    tool_result_messages_for_ollama.append({
                        "role": "tool",
                        "content": result_string_content 
                    })
                
                conversation.extend(tool_result_messages_for_ollama) # Add all tool results to conversation
            
            else: # No tool calls from assistant
                needs_user_input = True

if __name__ == "__main__":
    available_tools = [
        READ_FILE_DEFINITION,
        LIST_FILES_DEFINITION,
        EDIT_FILE_DEFINITION,
    ]
    
    agent = Agent(tools=available_tools, model_name="qwen3:8b") 
    agent.run()
