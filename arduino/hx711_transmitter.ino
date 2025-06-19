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

        int getTaredSensorValue(int arrayPos) {
            return sensorArray[arrayPos]->get_value(10);
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
            
            float taredTotalMeasure = 0.0;
            for (int i = 0; i < 4; ++i) {
                taredTotalMeasure += getTaredSensorValue(i);
            }
            
            float calibrationRatio = taredTotalMeasure / refWeight;
            
            float applyWeights[4] = {calibrationRatio, calibrationRatio, calibrationRatio, calibrationRatio};
            setScaleWeights(applyWeights);
      
        }

        void refreshReadings() {
            // get reading as scaled and with offset (get_units)
            for (int i = 0; i < 4; i++) {
                readingValues[i] = sensorArray[i]->get_units(10);
            }
        }

        float getIndividualReading(int sensorNumber) {
            if (sensorNumber < 0 || sensorNumber >= 4) return 0.0;
            return readingValues[sensorNumber];  
        }

        float getWeightReading() {
            float total = 0.0;
            for (int i = 0; i < 4; i++) {
                total += readingValues[i];
            }
            return total;
        }

        String getJsonReadings() {
            StaticJsonDocument<256> doc;
            for (int i = 0; i < 4; i++) {
                String sensor = "sensor_" + String(i);
                doc[sensor] = String(getIndividualReading(i), 2);
            }
            doc["weight"] = String(getWeightReading(), 2);

            String jsonReadings;
            serializeJson(doc, jsonReadings);

            return jsonReadings;
        }

        String getJsonCalibration() {
            StaticJsonDocument<256> doc;
            float calibration[4];

            for (int i = 0; i < 4; i++) {
                calibration[i] = sensorArray[i]->get_scale();
            }
            doc["calibration"] = calibration;
            
            String calibrationValues;
            serializeJson(doc, calibrationValues);

            return calibrationValues;
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
    
    if (storedCalibrationRatios.size() != 4) {
        Serial.println("Calibration array from memory is wrong size!");
        return nullptr;
    }

    static float outCalibrationRatios[4];
    for (int i = 0; i < 4; i++) {
        outCalibrationRatios[i] = storedCalibrationRatios[i];
    }

    return outCalibrationRatios;
}

void loop() {
    checkSerialCommands();
    sensorSystem.refreshReadings();
    Serial.println(sensorSystem.getJsonReadings());
    delay(500);
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
    input = ""; // clear input after processing
}
