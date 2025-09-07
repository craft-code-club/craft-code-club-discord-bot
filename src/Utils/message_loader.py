import os
import inspect


def load_message(filename: str) -> str:
    # Get the caller's file path
    caller_frame = inspect.stack()[1]
    caller_folder = os.path.dirname(caller_frame.filename)

    file_path = os.path.join(caller_folder, filename)

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            return content
    except FileNotFoundError:
        raise FileNotFoundError(f"Message file '{filename}' not found.")
    except UnicodeDecodeError:
        raise UnicodeDecodeError(f"Error reading '{filename}': Invalid file encoding. Please ensure the file is saved in UTF-8.")
    except PermissionError:
        raise PermissionError(f"Error reading '{filename}': Permission denied.")
    except Exception as e:
        raise Exception(f"Error loading message from '{filename}': {str(e)}")
