import os
class MessageLoader:

    def __init__(self):
        # Get the Messages directory path
        self.messages_dir = os.path.dirname(os.path.abspath(__file__))

    def load_message(self, filename: str) -> str:
        file_path = os.path.join(self.messages_dir, filename)

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


# Create a global instance for easy importing
message_loader = MessageLoader()

def load_message(filename: str) -> str:
    return message_loader.load_message(filename)
