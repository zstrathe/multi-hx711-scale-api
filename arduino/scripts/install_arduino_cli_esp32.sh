#!/bin/bash

set -e  # Exit on error

# Define CLI install location
INSTALL_DIR="$(pwd)/bin"
CLI_VERSION="latest"

echo "§ Installing Arduino CLI..."

# Download and install Arduino CLI
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh

# Ensure it's in your PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "§ Adding $INSTALL_DIR to PATH in ~/.bashrc"
    echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> ~/.bashrc
    export PATH="$PATH:$INSTALL_DIR"
fi

# Initialize arduino-cli config
echo "§ Initializing Arduino CLI..."
if arduino-cli config init; then
    echo "Config initialized."
else
    echo "Config already exists. Skipping init."
fi

# Add ESP32 board support
echo "§ Adding ESP32 board support URL..."
arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json

# Update board index
echo "§ Updating board index..."
arduino-cli core update-index

# Install ESP32 core
echo "§ Installing ESP32 core..."
arduino-cli core install esp32:esp32

# Install HX711 library
echo "§ Installing HX711 library..."
arduino-cli lib install "HX711" "ArduinoJson"

# Reload bash config
echo "§ Reloading bash config..."
source ~/.bashrc

echo "§ Everything installed!"
echo "§   You may need to restart your terminal to reload PATH."
echo "§   To verify: run 'arduino-cli board list' with your Nano ESP32 plugged in."
