import os
import logging
import zipfile
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zip_file_watcher.log'),
        logging.StreamHandler()
    ]
)

class ZipFileHandler(FileSystemEventHandler):
    def __init__(self, watch_dir, data_dir):
        self.watch_dir = watch_dir
        self.data_dir = data_dir
        self.processed_files = set()

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        if file_path.endswith('.zip') and file_path not in self.processed_files:
            self.processed_files.add(file_path)
            self.extract_zip_file(file_path)

    def extract_zip_file(self, zip_path):
        """Extract the zip file to the data directory."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.data_dir)
                logging.info(f"Extracted: {zip_path} to {self.data_dir}")
        except zipfile.BadZipFile as e:
            logging.error(f"Failed to extract {zip_path}: Bad zip file: {e}")
        except Exception as e:
            logging.error(f"Error extracting zip file {zip_path}: {e}")

class ZipFileWatcher:
    def __init__(self, watch_dir="watch", data_dir="data"):
        self.watch_dir = os.path.join(os.getcwd(), watch_dir)
        self.data_dir = os.path.join(os.getcwd(), data_dir)

    def setup_directories(self):
        """Create watch and data directories if they don't exist."""
        try:
            os.makedirs(self.watch_dir, exist_ok=True)
            logging.info(f"Watch directory ensured at: {self.watch_dir}")
        except Exception as e:
            logging.error(f"Failed to create watch directory: {e}")
            raise

        try:
            os.makedirs(self.data_dir, exist_ok=True)
            logging.info(f"Data directory ensured at: {self.data_dir}")
        except Exception as e:
            logging.error(f"Failed to create data directory: {e}")
            raise

    def watch_for_zip_files(self):
        """Watch the directory for new zip files and extract them."""
        self.setup_directories()
        logging.info("Watching for new zip files...")

        event_handler = ZipFileHandler(self.watch_dir, self.data_dir)
        observer = Observer()
        observer.schedule(event_handler, self.watch_dir, recursive=False)
        observer.start()

        try:
            while True:
                # Keep the script running
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logging.info("Stopping watch due to keyboard interrupt.")
        except Exception as e:
            logging.error(f"Error while watching directory: {e}")
            observer.stop()

        observer.join()

def main():
    try:
        watcher = ZipFileWatcher()
        watcher.watch_for_zip_files()
    except Exception as e:
        logging.error(f"Program failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    import time
    exit(main())
