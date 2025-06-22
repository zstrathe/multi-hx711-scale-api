#include <ArduinoJson.h>
#include <Preferences.h>
#include "HX711Sensors.h"

Preferences prefs;
Sensors sensorSystem;
String input;

void setup() {
    Serial.begin(115200);
    float* sensorScaleWeights = getSavedCalibrationFromMemory();
    sensorSystem.begin(sensorScaleWeights);
}

void loop() {
    checkSerialCommands();
    sensorSystem.refreshReadings();
    Serial.println(sensorSystem.getJsonReadings());
    delay(500);
}

void saveCalibrationToMemory(const String& jsonString) {
    // use Preferences to store calibration JSON in arduino memory
    prefs.begin("config", false); // false = read/write
    prefs.putString("jsonCalibration", jsonString);
    prefs.end();
    Serial.println("JSON calibrations saved to Preferences");
}

float* getSavedCalibrationFromMemory() {
    prefs.begin("config", true);
    String jsonString = prefs.getString("jsonCalibration");
    prefs.end();

    if (jsonString.length() == 0) {
        Serial.println("No JSON found saved in Preferences memory");
        return nullptr;
    }

    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, jsonString);
    if (error) {
        Serial.println("Failed to parse JSON");
        Serial.println(error.c_str());
        return nullptr;
    }

    JsonArray storedCalibrationRatios = doc["calibration"];

    if (!storedCalibrationRatios || storedCalibrationRatios.isNull()) {
        Serial.println("Calibration array from memory is empty!");
        return nullptr;
    }
    
    if (storedCalibrationRatios.size() != N_SENSORS) {
        Serial.println("Calibration array from memory is wrong size!");
        return nullptr;
    }

    static float outCalibrationRatios[N_SENSORS];
    for (int i = 0; i < N_SENSORS; i++) {
        outCalibrationRatios[i] = storedCalibrationRatios[i];
    }

    return outCalibrationRatios;
}

void sendResponseMessage(const String& message, const String& uuid, bool status) {
    StaticJsonDocument<512> response;
    response["message"] = message;
    response["message_uuid"] = uuid;
    response["status"] = status ? "success": "failed";
    serializeJson(response, Serial);
    Serial.println();
}

void checkSerialCommands() {
    input = ""; // clear input before reading
    if (Serial.available()) {
        input = Serial.readStringUntil('\n');
        input.trim();

        StaticJsonDocument<256> doc;
        DeserializationError error = deserializeJson(doc, input);

        if (error) {
            sendResponseMessage("invalid command", "unknown", false);
            return;
        }

        String message = doc["message"] | "";
        String message_uuid = doc["message_uuid"] | "unknown";

        if (message.startsWith("CALIBRATE:")) {
            float refWeight = message.substring(10).toFloat();
            sensorSystem.doCalibration(refWeight);
            String calibrationJsonString = sensorSystem.getJsonCalibration();

            sendResponseMessage(calibrationJsonString, message_uuid, true);
           
            saveCalibrationToMemory(calibrationJsonString);

        } else if (message == "TARE") {
            sensorSystem.tareSensors();
            
            sendResponseMessage("tare success", message_uuid, true);
        }
    }
}
