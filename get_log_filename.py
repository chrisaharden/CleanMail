import json
import sys

def read_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_log_filename.py <config_file_path>")
        sys.exit(1)

    config_file_path = sys.argv[1]
    try:
        config = read_config(config_file_path)
        log_file = config.get('LogFile', 'log.txt')
        print(log_file)
    except FileNotFoundError:
        print("log.txt")  # Default if config file not found
    except json.JSONDecodeError:
        print("log.txt")  # Default if JSON is invalid
