import os
import shutil
import re
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('file_processor.log'),
        logging.StreamHandler()
    ]
)

class FileProcessor:
    def __init__(self, data_dir="data", output_dir="output"):
        self.cwd = os.getcwd()
        self.data_dir = os.path.join(self.cwd, data_dir)
        self.output_dir = os.path.join(self.cwd, output_dir)
        self.filename_mapping = {}  # Dictionary to store original and new filenames
        self.current_output_path = None  # Track the current output path

    def setup_output_directory(self, top_level_folder):
        """Create top-level output directory if it doesn't exist."""
        try:
            output_path = os.path.join(self.output_dir, top_level_folder)
            os.makedirs(output_path, exist_ok=True)
            logging.info(f"Output directory ensured at: {output_path}")
            self.current_output_path = output_path  # Store the current output path
            return output_path
        except Exception as e:
            logging.error(f"Failed to create output directory: {e}")
            raise

    def clean_parent_folder_name(self, folder_name):
        """Clean parent folder name according to rules."""
        # Remove date pattern (handle both space and underscore formats)
        folder_name = re.sub(r'\d{2}[\s_]+\d{2}[\s_]+\d{4}[\s_]*-[\s_]*', '', folder_name)
        # Remove GUID pattern
        folder_name = re.sub(r'\s+[a-f0-9]{32}$', '', folder_name)
        # Strip any extra whitespace
        folder_name = folder_name.strip()
        # Replace spaces with underscores
        folder_name = folder_name.replace(' ', '_')
        return folder_name

    def clean_filename(self, filename, parent_folder_name=None):
        """Clean filename according to rules."""
        # Remove .md extension temporarily
        base_name = filename[:-3] if filename.endswith('.md') else filename

        # Remove date pattern (handle both space and underscore formats)
        base_name = re.sub(r'\d{2}[\s_]+\d{2}[\s_]+\d{4}[\s_]*-[\s_]*', '', base_name)

        # Remove GUID pattern
        base_name = re.sub(r'\s+[a-f0-9]{32}$', '', base_name)

        # Strip any extra whitespace
        base_name = base_name.strip()

        # If this is from a subdirectory, prepend the parent folder name
        if parent_folder_name:
            cleaned_parent = self.clean_parent_folder_name(parent_folder_name)
            base_name = f"{cleaned_parent}_{base_name}"

        # Replace remaining spaces with underscores
        base_name = base_name.replace(' ', '_')

        # Remove any double underscores that might have been created
        while '__' in base_name:
            base_name = base_name.replace('__', '_')

        # Remove any trailing underscores before adding extension
        base_name = base_name.rstrip('_')

        # Add back .md extension
        return f"{base_name}.md"

    def save_mapping(self):
        """Save the filename mapping to a file."""
        try:
            if not self.current_output_path:
                logging.error("No current output path set for saving mapping.")
                return
            mapping_file_path = os.path.join(self.current_output_path, "mapping.txt")
            with open(mapping_file_path, "w") as mapping_file:
                for original, new in self.filename_mapping.items():
                    mapping_file.write(f"{original} -> {new}\n")
            logging.info(f"Filename mapping saved to: {mapping_file_path}")
        except Exception as e:
            logging.error(f"Failed to save filename mapping: {e}")
            raise

    def process_files(self):
        """Process all files in the data directory."""
        try:
            if not os.path.exists(self.data_dir):
                logging.error(f"Data directory not found: {self.data_dir}")
                raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

            for root, dirs, files in os.walk(self.data_dir):
                # Get the relative path parts to determine where we are in the directory tree
                path_parts = Path(root).relative_to(self.data_dir).parts

                if len(path_parts) == 0:
                    # We are at the root level of the data directory
                    for dir_name in dirs:
                        # Clean the root folder name to create a top-level output folder
                        cleaned_root_folder = self.clean_parent_folder_name(dir_name)
                        self.setup_output_directory(cleaned_root_folder)
                else:
                    # We are processing a subdirectory or files within it
                    parent_folder_name = path_parts[0]
                    cleaned_parent_folder_name = self.clean_parent_folder_name(parent_folder_name)
                    output_path = os.path.join(self.output_dir, cleaned_parent_folder_name)

                    for file in files:
                        if file.endswith('.md'):
                            try:
                                # Create the new filename
                                new_filename = self.clean_filename(file, path_parts[-1] if len(path_parts) > 1 else None)
                                src_path = os.path.join(root, file)
                                dst_path = os.path.join(output_path, new_filename)

                                # Track the original and new filenames
                                self.filename_mapping[file] = new_filename

                                # Check if destination file already exists
                                if os.path.exists(dst_path):
                                    logging.warning(f"File already exists, skipping: {dst_path}")
                                    continue

                                # Copy file and preserve modification time
                                shutil.copy2(src_path, dst_path)
                                logging.info(f"Processed: {file} -> {new_filename}")

                            except PermissionError as e:
                                logging.error(f"Permission error processing file {file}: {e}")
                            except Exception as e:
                                logging.error(f"Error processing file {file}: {e}")

            # Save the filename mapping
            self.save_mapping()

        except Exception as e:
            logging.error(f"Error during file processing: {e}")
            raise

    def read_mapping(self):
        """Read the filename mapping from the mapping file."""
        if not self.current_output_path:
            logging.error("No current output path set for reading mapping.")
            return {}
        mapping_file_path = os.path.join(self.current_output_path, "mapping.txt")
        mapping = {}
        try:
            with open(mapping_file_path, "r") as mapping_file:
                for line in mapping_file:
                    original, new = line.strip().split(" -> ")
                    mapping[original] = new
            logging.info(f"Filename mapping read from: {mapping_file_path}")
        except Exception as e:
            logging.error(f"Failed to read filename mapping: {e}")
            raise
        return mapping

    def process_links(self):
        """Process links in all output markdown files and rewrite them with correct filenames."""
        try:
            mapping = self.read_mapping()
            if not mapping:
                logging.error("No mapping available to process links.")
                return
            for root, _, files in os.walk(self.current_output_path):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        new_lines = []
                        with open(file_path, 'r') as md_file:
                            for line in md_file:
                                # Extract links from the line (assuming markdown link format)
                                matches = re.findall(r'\[.*?\]\((.*?)\)', line)
                                for match in matches:
                                    # Decode the URL
                                    decoded_link = urllib.parse.unquote(match)
                                    filename = os.path.basename(decoded_link)
                                    if filename in mapping:
                                        # Replace with the new filename from mapping
                                        new_filename = mapping[filename]
                                        line = line.replace(match, new_filename)
                                new_lines.append(line)

                        # Write updated lines back to the file
                        with open(file_path, 'w') as md_file:
                            md_file.writelines(new_lines)

                        logging.info(f"Updated links in: {file_path}")
        except Exception as e:
            logging.error(f"Error processing links: {e}")
            raise

class Watcher:
    def __init__(self, directory_to_watch, processor):
        self.observer = Observer()
        self.directory_to_watch = directory_to_watch
        self.processor = processor

    def run(self):
        event_handler = Handler(self.processor)
        self.observer.schedule(event_handler, self.directory_to_watch, recursive=True)
        self.observer.start()
        try:
            while True:
                pass  # Keep running
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

class Handler(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor

    def on_any_event(self, event):
        if event.is_directory or not event.src_path.endswith('.md'):
            return
        # Run the processing when changes are detected
        self.processor.process_files()
        self.processor.process_links()

def main():
    try:
        processor = FileProcessor()
        processor.process_files()
        # Process links in the output files
        processor.process_links()
        logging.info("File processing completed successfully")

        # Start watching the data directory for changes
        watcher = Watcher(processor.data_dir, processor)
        watcher.run()
    except Exception as e:
        logging.error(f"Program failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
