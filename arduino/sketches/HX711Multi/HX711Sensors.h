#include "HX711.h"
#include <ArduinoJson.h>

#define N_SENSORS 4

int esp32Sck = D13;
int esp32DIO[] = {D0, D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12};

class Sensors {
    private:
        HX711** sensorArray;
        float* readingValues;
    
    public:
        Sensors() {
            int maxPins = sizeof(esp32DIO) / sizeof(esp32DIO[0]);
            if (N_SENSORS > maxPins) {
                Serial.println("Error: Not enough DIO pins for N_SENSORS");
                while (true);  // Halt execution
            }
            sensorArray = new HX711*[N_SENSORS];
            readingValues = new float[N_SENSORS];
            for (int i = 0; i < N_SENSORS; i++) {
                sensorArray[i] = new HX711();
                sensorArray[i]->begin(esp32DIO[i], esp32Sck);
                readingValues[i] = 0.0;
            }
        }

        ~Sensors() {
            for (int i = 0; i < N_SENSORS; i++) {
                delete sensorArray[i];
            }
            delete[] sensorArray;
            delete[] readingValues;
        }

        // read_average(times) -> raw average of readings for number of times specified
        // get_value(times) -> read_average minus OFFSET
        // get_units(times) -> read_average minus OFFSET divided by SCALE
        

        void begin(float* scale_weights) {
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
            for (int i = 0; i < N_SENSORS; i++) {
                sensorArray[i]->tare();
            }
        }

        void setScaleWeights(float* scale_weights) {
            for (int i = 0; i < N_SENSORS; i++) {
                sensorArray[i]->set_scale(scale_weights[i]);
            }
        }

        void doCalibration(float refWeight) {
            for (int i = 0; i < N_SENSORS; ++i) {
                sensorArray[i]->set_scale();
                sensorArray[i]->tare();
            }

            Serial.println("Place weight...");
            //TODO: UPDATE TO DETECT WHEN WEIGHT IS PLACED???
            delay(5000);  // Wait 5 sec for manual placement
            
            float taredTotalMeasure = 0.0;
            for (int i = 0; i < N_SENSORS; ++i) {
                taredTotalMeasure += getTaredSensorValue(i);
            }
            
            float calibrationRatio = taredTotalMeasure / refWeight;
            
            float applyWeights[N_SENSORS];
            for (int i = 0; i < N_SENSORS; i++) {
                applyWeights[i] = calibrationRatio;
            }
            setScaleWeights(applyWeights);
        }

        void refreshReadings() {
            // get reading as scaled and with offset (get_units)
            for (int i = 0; i < N_SENSORS; i++) {
                readingValues[i] = sensorArray[i]->get_units(10);
            }
        }

        float getIndividualReading(int sensorNumber) {
            if (sensorNumber < 0 || sensorNumber >= N_SENSORS) return 0.0;
            return readingValues[sensorNumber];  
        }

        float getWeightReading() {
            float total = 0.0;
            for (int i = 0; i < N_SENSORS; i++) {
                total += readingValues[i];
            }
            return total;
        }

        String getJsonReadings() {
            StaticJsonDocument<128 + N_SENSORS * 32> doc;
            for (int i = 0; i < N_SENSORS; i++) {
                String sensor = "sensor_" + String(i);
                doc[sensor] = String(getIndividualReading(i), 2);
            }
            doc["weight"] = String(getWeightReading(), 2);

            String jsonReadings;
            serializeJson(doc, jsonReadings);

            return jsonReadings;
        }

        String getJsonCalibration() {
            StaticJsonDocument<128 + N_SENSORS * 32> doc;
            float calibration[N_SENSORS];

            for (int i = 0; i < N_SENSORS; i++) {
                calibration[i] = sensorArray[i]->get_scale();
            }
            doc["calibration"] = calibration;
            
            String calibrationValues;
            serializeJson(doc, calibrationValues);

            return calibrationValues;
        }
};