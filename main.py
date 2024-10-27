import os
import shutil
import re
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path

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

    def setup_output_directory(self):
        """Create output directory if it doesn't exist."""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            logging.info(f"Output directory ensured at: {self.output_dir}")
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
            mapping_file_path = os.path.join(self.output_dir, "mapping.txt")
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
            self.setup_output_directory()

            if not os.path.exists(self.data_dir):
                logging.error(f"Data directory not found: {self.data_dir}")
                raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

            for root, dirs, files in os.walk(self.data_dir):
                # Get the parent folder name if we're in a subdirectory
                path_parts = Path(root).relative_to(self.data_dir).parts
                parent_folder_name = None

                if len(path_parts) == 2:  # We're in a subdirectory
                    # Get the immediate parent directory name (the one with Event Bridge)
                    parent_folder = os.path.basename(root)
                    parent_folder_name = parent_folder

                for file in files:
                    if file.endswith('.md'):
                        try:
                            # Create the new filename
                            new_filename = self.clean_filename(file, parent_folder_name)
                            src_path = os.path.join(root, file)
                            dst_path = os.path.join(self.output_dir, new_filename)

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
        mapping_file_path = os.path.join(self.output_dir, "mapping.txt")
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
            for root, _, files in os.walk(self.output_dir):
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


def main():
    try:
        processor = FileProcessor()
        processor.process_files()
        # Process links in the output files
        processor.process_links()
        logging.info("File processing completed successfully")
    except Exception as e:
        logging.error(f"Program failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
