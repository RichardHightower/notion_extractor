#!/bin/bash

# Delete the directories if they exist
for dir in "data" "output" "watch"; do
    if [ -d "$PWD/$dir" ]; then
        echo "Deleting $PWD/$dir..."
        rm -rf "$PWD/$dir"
    else
        echo "$PWD/$dir does not exist. Skipping..."
    fi
done

rm *.log

echo "Cleanup complete."

mkdir data
