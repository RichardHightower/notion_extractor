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
    def __init__(self, data_dir="data", flat_output_dir="output/flat", files_output_dir="output/files"):
        self.cwd = os.getcwd()
        self.data_dir = os.path.join(self.cwd, data_dir)
        self.flat_output_dir = os.path.join(self.cwd, flat_output_dir)
        self.files_output_dir = os.path.join(self.cwd, files_output_dir)
        self.filename_mapping = {}  # Dictionary to store original and new filenames
        self.setup_output_directories()

    def setup_output_directories(self):
        """Create output directories if they don't exist."""
        try:
            os.makedirs(self.flat_output_dir, exist_ok=True)
            os.makedirs(self.files_output_dir, exist_ok=True)
            logging.info(f"Output directories ensured at: {self.flat_output_dir} and {self.files_output_dir}")
        except Exception as e:
            logging.error(f"Failed to create output directories: {e}")
            raise

    def extract_title_from_content(self, content):
        """Extract title from markdown content."""
        # Look for # Title or # Header pattern
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()

        # If no # title, try first line
        first_line = content.strip().split('\n')[0].strip()
        if first_line:
            # Remove any markdown heading characters
            return re.sub(r'^#+\s*', '', first_line)

        return None

    def combine_files_with_titles(self):
        """Combine all markdown files into one with title delimiters."""
        try:
            combined_content = []

            # Walk through the data directory
            for root, _, files in os.walk(self.data_dir):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()

                                # Extract title from content
                                title = self.extract_title_from_content(content)
                                if not title:
                                    # Use filename as fallback
                                    title = os.path.splitext(file)[0]

                                # Add delimited content
                                combined_content.append(f"--- {title} ---\n{content.strip()}\n")

                        except Exception as e:
                            logging.error(f"Error processing file {file}: {e}")

            # Write combined content to output file
            output_file = os.path.join(self.files_output_dir, 'combined.md')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(combined_content))

            logging.info(f"Created combined file at: {output_file}")

        except Exception as e:
            logging.error(f"Error creating combined file: {e}")
            raise

    def clean_parent_folder_name(self, folder_name):
        """Clean parent folder name according to rules."""
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
            mapping_file_path = os.path.join(self.flat_output_dir, "mapping.txt")
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

            # Process files for flat directory
            for root, _, files in os.walk(self.data_dir):
                path_parts = Path(root).relative_to(self.data_dir).parts
                for file in files:
                    if file.endswith('.md'):
                        try:
                            # Create the new filename
                            new_filename = self.clean_filename(
                                file,
                                path_parts[-1] if len(path_parts) > 0 else None
                            )
                            src_path = os.path.join(root, file)
                            dst_path = os.path.join(self.flat_output_dir, new_filename)

                            # Track the original and new filenames
                            self.filename_mapping[file] = new_filename

                            # Copy file and preserve modification time
                            shutil.copy2(src_path, dst_path)
                            logging.info(f"Processed: {file} -> {new_filename}")

                        except Exception as e:
                            logging.error(f"Error processing file {file}: {e}")

            # Save the filename mapping
            self.save_mapping()

            # Create combined file
            self.combine_files_with_titles()

        except Exception as e:
            logging.error(f"Error during file processing: {e}")
            raise

    def read_mapping(self):
        """Read the filename mapping from the mapping file."""
        mapping_file_path = os.path.join(self.flat_output_dir, "mapping.txt")
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

    def delete_mapping_file(self):
        """Delete the mapping file after processing is complete."""
        try:
            mapping_file_path = os.path.join(self.flat_output_dir, "mapping.txt")
            if os.path.exists(mapping_file_path):
                os.remove(mapping_file_path)
                logging.info(f"Deleted mapping file: {mapping_file_path}")
            else:
                logging.warning(f"Mapping file not found at: {mapping_file_path}")
        except Exception as e:
            logging.error(f"Failed to delete mapping file: {e}")
            raise

    def process_links(self):
        """Process links in all output markdown files."""
        try:
            mapping = self.read_mapping()
            if not mapping:
                logging.error("No mapping available to process links.")
                return

            # Process links in flat directory
            for file in os.listdir(self.flat_output_dir):
                if file.endswith('.md'):
                    self.update_links_in_file(os.path.join(self.flat_output_dir, file), mapping)

            # Process links in combined file
            combined_file = os.path.join(self.files_output_dir, 'combined.md')
            if os.path.exists(combined_file):
                self.update_links_in_file(combined_file, mapping)

            # Delete the mapping file after processing is complete
            self.delete_mapping_file()

        except Exception as e:
            logging.error(f"Error processing links: {e}")
            raise

    def update_links_in_file(self, file_path, mapping):
        """Update links in a single file."""
        try:
            new_lines = []
            with open(file_path, 'r') as md_file:
                for line in md_file:
                    # Extract links from the line
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
            logging.error(f"Error updating links in {file_path}: {e}")
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