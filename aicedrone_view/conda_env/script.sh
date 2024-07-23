#!/bin/bash

# Export file name
IMPORT_FILE="aicedrone_view_yolo.yaml"

# Create environment from configuration file
echo "Creating environment from $IMPORT_FILE..."
conda env create --file $IMPORT_FILE

echo "The environment has been successfully created"
