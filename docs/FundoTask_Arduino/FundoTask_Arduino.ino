#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// ---- CONFIG ----
const char* ssid = "Inacapino 2.4G";
const char* pass = "27081941";   // <- pon tu clave real
const char* url  = "http://192.168.1.3:8000/api/lecturas/";  // IP de tu PC

const int TRIG = D5;
const int ECHO = D6;

// ---- MEDIDAS (botella deportiva, mídelas por DENTRO) ----
const float ALTURA_TOTAL = 26.0;  // cm: del sensor al fondo (22 de botella + ~4 de espacio)
const float DIST_MIN     = 4.0;   // cm: distancia sensor-agua con la botella llena
const float H_RECIPIENTE = 22.0;  // cm: altura interior (fondo a boca)
const float R_BASE       = 3.8;   // cm: radio en el fondo (mídelo)
const float R_TOPE       = 3.8;   // cm: radio en la boca (igual = cilindro)

// ---- VOLUMEN ----
// Tronco de cono: si R_BASE == R_TOPE, queda cilindro.
float calcularLitros(float nivel) {
  float r = R_BASE + (R_TOPE - R_BASE) * (nivel / H_RECIPIENTE);
  float cm3 = PI * nivel / 3.0 * (R_BASE * R_BASE + R_BASE * r + r * r);
  return cm3 / 1000.0;
}

// ---- SENSOR ----
float medirDistancia() {
  digitalWrite(TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long dur = pulseIn(ECHO, HIGH, 30000);
  return dur * 0.0343 / 2;
}

float medirPromedio() {
  float suma = 0; int n = 0;
  for (int i = 0; i < 5; i++) {
    float d = medirDistancia();
    if (d > 2 && d < 400) { suma += d; n++; }
    delay(60);
  }
  return n > 0 ? suma / n : -1;
}

// ---- SETUP ----
void setup() {
  Serial.begin(115200);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  WiFi.begin(ssid, pass);
  Serial.print("Conectando");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

// ---- LOOP ----
void loop() {
  float d = medirPromedio();
  if (d > 0 && WiFi.status() == WL_CONNECTED) {
    float nivel  = constrain(ALTURA_TOTAL - d, 0, ALTURA_TOTAL - DIST_MIN);
    float pct    = nivel / (ALTURA_TOTAL - DIST_MIN) * 100.0;
    float litros = calcularLitros(nivel);
    float ml     = litros * 1000.0;

    String json = "{\"distancia\":" + String(d, 1) +
                  ",\"nivel_cm\":" + String(nivel, 1) +
                  ",\"porcentaje\":" + String(pct, 1) +
                  ",\"litros\":" + String(litros, 3) + "}";

    WiFiClient client;
    HTTPClient http;
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(json);

    Serial.printf("Dist: %.1f cm | Nivel: %.1f cm | %.0f%% | %.3f L (%.0f ml) | HTTP %d\n",
                  d, nivel, pct, litros, ml, code);
    http.end();
  } else {
    Serial.println("Lectura inválida o sin WiFi");
  }
  delay(5000);
}