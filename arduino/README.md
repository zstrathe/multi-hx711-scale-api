# How to Use install_arduino_cli_esp32.sh on Raspberry Pi

Follow these steps to download, make executable, and run the Arduino CLI + ESP32 setup script.


## ✅ Step 1: Make It Executable
Before running the script, you must make it executable:

```bash
cd scripts
chmod +x install_arduino_cli_esp32.sh
```

## 🚀 Step 2: Run the Script
Now you can run the script like this:

```bash
./install_arduino_cli_esp32.sh
```
This will install Arduino CLI, configure ESP32 board support, and update your ~/.bashrc PATH if needed.

## 🧪 Step 3: Verify Installation
After running the script, verify it worked by checking connected boards:

```bash
arduino-cli board list
```

## Step 4: Compile and Upload Sketch to Arduino
And compile/upload a sketch (replace MyProject with your sketch folder: i.e.: "sketches/HX711Multi"):

```bash
arduino-cli compile --fqbn esp32:esp32:nano_esp32 sketches/HX711Multi
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:nano_esp32 sketches/HX711Multi
```

## 📝 Tips
#### 1: If arduino-cli is still not found after running the script, restart your terminal or manually run:

```bash
source ~/.bashrc
```

#### 2: You can monitor it with:

```bash
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200
```
