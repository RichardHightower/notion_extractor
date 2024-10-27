# Export and Zip File Watcher Setup Guide

These two programs turn an export of Notion into something that can be later easily imported into a vector database or used to create a website. 

This guide explains how to set up and run the Export Watcher and Zip File Watcher utilities. These programs monitor directories for file changes and perform automated actions on the files.

## Directory Structure

```
project/
├── data/                 # Directory monitored by export_watcher
├── output/               # Processed markdown files
└── watch/                # Directory for compressed archives
```

## System Overview

### Export Watcher
Monitors the `data/` directory for new markdown files and processes them by:
- Cleaning filenames (removing dates, GUIDs)
- Standardizing naming conventions
- Updating internal links between files
- Creating a mapping file of original to new filenames
- It then outputs them to `output/`

### Zip File Watcher
Monitors specific directories for changes and:
- Unzips ZIP archives of zip files dropped into watch
- Logs all activities

## Setup Instructions

### 1. Install Miniconda
1. Download Miniconda from: https://docs.conda.io/en/latest/miniconda.html
2. Run the installer:
   ```bash
   # Linux/Mac
   bash Miniconda3-latest-Linux-x86_64.sh
   
   # Windows
   # Run the .exe installer
   ```
3. Restart your terminal after installation

### 2. Create Conda Environment
```bash
# Create new environment named 'watcher'
conda create -n watcher python=3.9

# Activate the environment
conda activate watcher
```

### 3. Install Dependencies
```bash
# Install required packages
pip install watchdog
pip install pathlib
```



## Running the Programs

### Export Watcher
```bash
# Activate conda environment
conda activate watcher

# Start export watcher
python export_watcher.py
```

The Export Watcher will:
- Monitor the `data/` directory for new files
- Process any new markdown files automatically
- Create cleaned versions in the `output/` directory
- Generate a mapping file of filename changes

### Zip File Watcher
```bash
# In a new terminal window
conda activate watcher

# Start zip file watcher
python zip_file_watcher.py
```

The Zip File Watcher will:
- Monitor configured directories for changes
- Unzip ZIP archives when they are added to watch

## Common Operations

### Checking Logs
Both watchers create log files in their respective directories:
```bash
# View export watcher logs
tail -f export_watcher.log

# View zip watcher logs
tail -f zip_watcher.log
```

### Stopping the Watchers
Press `Ctrl+C` in each terminal window to stop the watchers.

### Updating Dependencies
```bash
conda activate watcher
pip freeze > requirements.txt
pip install -r requirements.txt
```
# Code walkthrough 

## Zip File Watcher 

Let me break down this program step by step. This is a zip file monitoring program that watches for new zip files and automatically extracts them.

1. **Initial Setup**
```python
# Sets up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zip_file_watcher.log'),
        logging.StreamHandler()
    ]
)
```
- Creates a log file called 'zip_file_watcher.log'
- Also shows logs in the console
- Logs include timestamps and severity levels

2. **ZipFileHandler Class**
```python
class ZipFileHandler(FileSystemEventHandler):
    def __init__(self, watch_dir, data_dir):
        self.watch_dir = watch_dir
        self.data_dir = data_dir
        self.processed_files = set()  # Keeps track of processed files
```
This class:
- Inherits from watchdog's FileSystemEventHandler
- Tracks which files have been processed
- Stores watch and data directory paths

3. **File Detection**
```python
def on_created(self, event):
    if event.is_directory:
        return

    file_path = event.src_path
    if file_path.endswith('.zip') and file_path not in self.processed_files:
        self.processed_files.add(file_path)
        self.extract_zip_file(file_path)
```
When a new file appears:
- Checks if it's a file (not a directory)
- Verifies it's a .zip file
- Ensures it hasn't been processed before
- Triggers extraction if conditions are met

4. **Zip Extraction**
```python
def extract_zip_file(self, zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.data_dir)
            logging.info(f"Extracted: {zip_path} to {self.data_dir}")
    except zipfile.BadZipFile as e:
        logging.error(f"Failed to extract {zip_path}: Bad zip file: {e}")
```
- Opens the zip file
- Extracts all contents to the data directory
- Logs success or failure
- Handles corrupted zip files

5. **ZipFileWatcher Class**
```python
class ZipFileWatcher:
    def __init__(self, watch_dir="watch", data_dir="data"):
        self.watch_dir = os.path.join(os.getcwd(), watch_dir)
        self.data_dir = os.path.join(os.getcwd(), data_dir)
```
- Sets up directories relative to current working directory
- Default directories are "watch" and "data"

6. **Directory Setup**
```python
def setup_directories(self):
    os.makedirs(self.watch_dir, exist_ok=True)
    os.makedirs(self.data_dir, exist_ok=True)
```
- Creates required directories if they don't exist
- Logs directory creation or errors

7. **Watch Process**
```python
def watch_for_zip_files(self):
    self.setup_directories()
    event_handler = ZipFileHandler(self.watch_dir, self.data_dir)
    observer = Observer()
    observer.schedule(event_handler, self.watch_dir, recursive=False)
    observer.start()
```
- Sets up directories
- Creates an event handler
- Starts watching the directory
- Non-recursive (doesn't watch subdirectories)

8. **Main Loop**
```python
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
```
- Keeps program running indefinitely
- Can be stopped with Ctrl+C
- Gracefully handles interruption

Program Flow:
1. Program starts
2. Creates/verifies directories
3. Starts watching the 'watch' directory
4. When a new .zip file appears:
   - Checks if it's new and valid
   - Extracts contents to 'data' directory
   - Logs the operation
5. Continues watching until interrupted

To run the program:
```bash
python zip_file_watcher.py
```
Then:
1. Place zip files in the 'watch' directory
2. Program automatically extracts them to 'data' directory
3. Check logs for success/failure messages
4. Use Ctrl+C to stop the program


## Export Watcher 

Let me break down this program step by step. This is a file watcher and processor that handles markdown files, specifically focusing on cleaning filenames and updating internal links.

1. **Initial Setup**
```python
class FileProcessor:
    def __init__(self, data_dir="data", output_dir="output"):
        self.cwd = os.getcwd()
        self.data_dir = os.path.join(self.cwd, data_dir)
        self.output_dir = os.path.join(self.cwd, output_dir)
        self.filename_mapping = {}
        self.current_output_path = None
```
- Sets up working directories: 'data' for input and 'output' for processed files
- Initializes a mapping dictionary to track filename changes
- Sets up logging to both file and console

2. **Directory Structure Management**
```python
def setup_output_directory(self, top_level_folder):
    output_path = os.path.join(self.output_dir, top_level_folder)
    os.makedirs(output_path, exist_ok=True)
    self.current_output_path = output_path
```
- Creates output directories with cleaned names
- Maintains the current working output path

3. **Filename Cleaning**
The program cleans filenames in two ways:

For folders:
```python
def clean_parent_folder_name(self, folder_name):
    # Removes:
    # - Date patterns (10 24 2024)
    # - GUID patterns
    # - Extra spaces
    # Replaces spaces with underscores
```

For files:
```python
def clean_filename(self, filename, parent_folder_name=None):
    # Similar cleaning as folders
    # Can prepend parent folder name
    # Ensures consistent formatting
```

4. **File Processing**
```python
def process_files(self):
    # Walks through data directory
    # For each markdown file:
    # 1. Cleans the filename
    # 2. Creates appropriate output directory structure
    # 3. Copies file to new location
    # 4. Maintains mapping of old->new names
```

5. **Link Processing**
```python
def process_links(self):
    # Reads the filename mapping
    # For each markdown file in output:
    # 1. Finds all markdown links
    # 2. Decodes URLs
    # 3. Updates links to use new filenames
    # 4. Saves updated content
```

6. **File Watching**
```python
class Watcher:
    # Watches data directory for changes
    # When changes detected:
    # 1. Triggers file processing
    # 2. Updates links
```

Complete Process Flow:
1. Program starts and:
   - Creates necessary directories
   - Sets up logging
   - Initializes file processor

2. Initial Processing:
   - Processes all existing files
   - Creates clean filenames
   - Updates internal links

3. Continuous Watching:
   - Monitors data directory for changes
   - When a .md file changes:
     - Reprocesses files
     - Updates links
     - Maintains mapping file

4. For each file processed:
   - Original: `10 24 2024 - Document abc123.md`
   - Becomes: `Document.md`
   - Links inside are updated to match new names
   - Mapping is saved for reference

5. Error Handling:
   - Logs all operations
   - Handles file permissions
   - Manages duplicate files
   - Graceful error recovery

Example Flow:
```
Input: "10 24 2024 - Event Bridge 129d6bbdbbea80/Specification.md"
↓
Clean folder name: "Event_Bridge"
↓
Clean filename: "Event_Bridge_Specification.md"
↓
Update internal links to use new names
↓
Save mapping for reference
```

The program continues running until interrupted (Ctrl+C), constantly watching for new or modified files to process.
