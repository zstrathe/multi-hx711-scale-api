#include "HX711.h"
#include <ArduinoJson.h>
#include <Preferences.h>

#define LOADCELL_1_DOUT A0
#define LOADCELL_1_SCK A1
#define LOADCELL_2_DOUT A2
#define LOADCELL_2_SCK A3
#define LOADCELL_3_DOUT A4
#define LOADCELL_3_SCK A5
#define LOADCELL_4_DOUT 2
#define LOADCELL_4_SCK 3
#define N_SENSORS 4

class Sensors {
    public:
        HX711 hx1, hx2, hx3, hx4;
        HX711* sensorArray[4];
        float readingValues[4] = {0.0, 0.0, 0.0, 0.0};

        // read_average(times) -> raw average of readings for number of times specified
        // get_value(times) -> read_average minus OFFSET
        // get_units(times) -> read_average minus OFFSET divided by SCALE
        Sensors() {
            sensorArray[0] = &hx1;
            sensorArray[1] = &hx2;
            sensorArray[2] = &hx3;
            sensorArray[3] = &hx4;
        }

        void begin(float* scale_weights) {
            hx1.begin(LOADCELL_1_DOUT, LOADCELL_1_SCK);
            hx2.begin(LOADCELL_2_DOUT, LOADCELL_2_SCK);
            hx3.begin(LOADCELL_3_DOUT, LOADCELL_3_SCK);
            hx4.begin(LOADCELL_4_DOUT, LOADCELL_4_SCK);
            tareSensors();

            if (scale_weights != nullptr) {
                setScaleWeights(scale_weights);
            } else {
                Serial.println("Calibration is required for sensors!");
            }
        }

        void tareSensors() {
            // set initial offsets for sensors
            for (int i = 0; i < 4; i++) {
                sensorArray[i]->tare();
            }
        }

        void setScaleWeights(float* scale_weights) {
            for (int i = 0; i < 4; i++) {
                sensorArray[i]->set_scale(scale_weights[i]);
            }
        }

        // Calibrate all sensors
        void doCalibration(float refWeight) {
            for (int i = 0; i < 4; ++i) {
                sensorArray[i]->set_scale();
                sensorArray[i]->tare();
            }

            Serial.println("Place weight...");
            //TODO: UPDATE TO DETECT WHEN WEIGHT IS PLACED???
            delay(5000);  // Wait 5 sec for manual placement
            
            for (int i = 0; i < 4; ++i) {
                // get_units returns the value divided by scale, need to call get_value instead???
                float raw_units = sensorArray[i]->get_value(10);
                float scale_val = raw_units / refWeight;
                sensorArray[i]->set_scale(scale_val);
            }
        }

        void refreshReadings() {
            for (int i = 0; i < 4; i++) {
                readingValues[i] = sensorArray[i]->get_units(10);
            }
        }

        float getReading(int sensorNumber) {
            if (sensorNumber < 0 || sensorNumber >= 4) return 0.0;
            return readingValues[sensorNumber];  
        }

        float getAverageReading() {
            float total = 0.0;
            for (int i = 0; i < 4; i++) {
                total += readingValues[i];
            }
            return total / 4.0;
        }

        String getJsonReadings() {
            String jsonString = "{";
            for (int i = 0; i < 4; i++) {
                jsonString += "\"sensor_";
                jsonString += String(i);
                jsonString += "\":";
                jsonString += String(getReading(i), 2);
                jsonString += ",";
            }
            jsonString += "\"average\":"; 
            jsonString += String(getAverageReading(), 2);
            jsonString += "}";
            return jsonString;
        }

        String getJsonCalibration() {
            String jsonString = "{\"calibration\":[";

            for (int i = 0; i < 4; i++) {
                jsonString += String(sensorArray[i]->get_scale(), 5);
                if (i < 3) jsonString += ", ";
            }
            jsonString += "]}";
            return jsonString;
        }
};

Preferences prefs;
Sensors sensorSystem;
String input;

void setup() {
    Serial.begin(115200);
    float* sensorScaleWeights = getSavedCalibrationFromMemory();
    sensorSystem.begin(sensorScaleWeights);
}

void saveCalibrationToMemory(const String& jsonString) {
    // use Preferences to store calibration JSON in memory (EEPROM?)
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

    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, jsonString);
    if (error) {
        Serial.println("Failed to parse JSON");
        Serial.println(error.c_str());
        return nullptr;
    }

    JsonArray configWeights = doc["calibration"];

    if (!configWeights || configWeights.isNull()) {
        Serial.println("Calibration array from memory is empty!");
        return nullptr;
    }
    
    if (configWeights.size() != 4) {
        Serial.println("Calibration array from memory is wrong size!");
        return nullptr;
    }

    static float configValues[4];
    for (int i = 0; i < 4; i++) {
        configValues[i] = configWeights[i];
    }

    return configValues;
}

void loop() {
    checkSerialCommands();
    sensorSystem.refreshReadings();
    Serial.println(sensorSystem.getJsonReadings());
    delay(500);
}

void outputCommandStatusToSerial(bool statusSuccess, String output_data_json_string) {
    String statusString = statusSuccess ? "success" : "failed";
    String line = "{\"status\": \"" + statusString + "\", \"data\": " + output_data_json_string + "}";
    Serial.println(line); 
}

void checkSerialCommands() {
    if (Serial.available()) {
        input = Serial.readStringUntil('\n');
        input.trim();
    }

    if (input.startsWith("CALIBRATE:")) {
        float refWeight = input.substring(10).toFloat();
        sensorSystem.doCalibration(refWeight);
        String calibrationJsonString = sensorSystem.getJsonCalibration();
        outputCommandStatusToSerial(true, calibrationJsonString);
        saveCalibrationToMemory(calibrationJsonString);
    } else if (input == "TARE") {
        sensorSystem.tareSensors();
        outputCommandStatusToSerial(true, "{\"message\": \"tare success\"}");
    }

    input = ""; // clear input after processing
}


