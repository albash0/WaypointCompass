"""Module header pin maps and placement. Coordinates in millimeters."""
import json
from pathlib import Path


def row(ref, value, names, nets, xy, schematic, side="back", body=None):
    n = len(names)
    lo, hi = -(n - 1) * 1.27, (n - 1) * 1.27
    module = {
        "ref": ref, "value": value,
        "footprint": value.replace("-", "_").replace(" ", "_") + "_Socket",
        "side": side, "pcb_at": xy, "schematic_at": schematic,
        "pins": [{"number": str(i + 1), "name": name, "net": net,
                  "at": [round(lo + 2.54 * i, 3), 0]}
                 for i, (name, net) in enumerate(zip(names, nets))],
        "courtyard": [round(lo - 1.6, 3), -1.7, round(hi + 1.6, 3), 1.7],
        "socket_outlines": [[round(lo - 1.3, 3), -1.3, round(hi + 1.3, 3), 1.3]],
        "ref_at": [0, -3],
        "labels": [[ref + " " + value, 0, 4, 0.9]],
    }
    if body:
        module["body"] = body
    return module


espnames = (["TX / GPIO43", "RX / GPIO44"] + ["GPIO" + str(i) for i in range(1, 8)]
            + ["5V / USB", "GND", "3V3", "GPIO13", "GPIO12", "GPIO11", "GPIO10", "GPIO9", "GPIO8"])
espnets = (["GPS_RX", "GPS_TX", "BUTTON_1", "BUTTON_2"] + [None] * 5
           + ["5V_USB", "GND", "3V3", "TFT_DC", None, "TFT_MOSI", "TFT_SCK", "IMU_SCL", "IMU_SDA"])
esp = {
    "ref": "J1", "value": "ESP32-S3 SuperMini",
    "footprint": "ESP32_S3_SuperMini_2x09_Sockets", "side": "back",
    "pcb_at": [118.5, 113], "schematic_at": [76.2, 40.64],
    "pins": [{"number": str(i + 1), "name": name, "net": espnets[i],
              "at": [-7.62 if i < 9 else 7.62, round(-10.16 + (i % 9) * 2.54, 3)]}
             for i, name in enumerate(espnames)],
    "courtyard": [-9.25, -12.1, 9.25, 12.1],
    "socket_outlines": [[-8.92, -11.46, -6.32, 11.46], [6.32, -11.46, 8.92, 11.46]],
    "body": [-9, -11.75, 9, 11.75], "ref_at": [0, 0],
    "labels": [["USB", 0, -10, 0.8], ["J1 ESP32-S3", 0, 2, 1]],
}
tft = row("J2", "GC9A01 TFT", ["RST", "CS", "DC", "SDA / DIN", "SCL / CLK", "GND", "VCC"],
          ["3V3", "GND", "TFT_DC", "TFT_MOSI", "TFT_SCK", "GND", "3V3"],
          [154.74, 120], [152.4, 40.64], side="front", body=[-19, -43.74, 19, 1.76])
tft["rotation"] = 90
for i,pin in enumerate(tft["pins"]):
    pin["number"] = str(7-i)  # The supplied drawing marks VCC as pin 1.
tft["circles"] = [[0, -24.74, 19], [0, -24.74, 16.2]]
tft["labels"] = []
gps = row("J3", "GPS CABLE", ["VCC", "RX", "TX", "GND"],
          ["GPS_VCC", "GPS_RX", "GPS_TX", "GND"], [111.43, 133.02], [228.6, 40.64])
gps["labels"] = [["J3 GPS", 0, -3, 0.8], ["VCC RX TX GND", 0, 3, 0.8]]
imu = row("J4", "GY-521", ["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"],
          ["3V3", "GND", "IMU_SCL", "IMU_SDA", "AUX_SDA", "AUX_SCL", "GND", None],
          [138.5, 122.86], [152.4, 106.68], body=[-10, 0, 10, 16])
imu["labels"] = [["J4 GY-521", 0, 7, 1], ["+X FRONT", 0, 10, 0.8]]
mag = row("J5", "GY-271", ["DRDY / DD0Y", "SDA", "SCL", "GND", "VCC"],
          [None, "AUX_SDA", "AUX_SCL", "GND", "3V3"], [141, 102.54], [228.6, 106.68],
          body=[-7.5, 0, 7.5, 18])
mag["labels"] = [["J5 GY-271", 0, 7, 1], ["+X FRONT", 0, 10, 0.8]]
jp = row("JP1", "GPS VOLTAGE", ["3V3", "GPS VCC", "5V USB"],
         ["3V3", "GPS_VCC", "5V_USB"], [125.4, 133.02], [76.2, 106.68])
jp["labels"] = [["JP1", 0, -3, 0.8], ["3V3  V  5V", 0, 3, 0.8]]
def button(ref, signal, center_y, schematic_x):
    return {
        "ref": ref, "value": "6x6 tactile", "kind": "button",
        "footprint": "SW_PUSH_6mm", "side": "front",
        "pcb_at": [101.75, center_y-2.25],
        "schematic_at": [schematic_x, 152.4],
        "pins": [{"number": "1", "name": signal, "net": signal},
                 {"number": "2", "name": "GND", "net": "GND"}],
        "physical_pads": [{"number": "1", "at": [0, 0]},
                          {"number": "1", "at": [6.5, 0]},
                          {"number": "2", "at": [0, 4.5]},
                          {"number": "2", "at": [6.5, 4.5]}],
        "labels": [[ref, 3.25, -4.5, 0.8]],
        "body_center": [105, center_y],
    }
sw1 = button("SW1", "BUTTON_1", 111.5, 76.2)
sw2 = button("SW2", "BUTTON_2", 127, 152.4)
config = {
    "status": "Header pin orders supplied by user; TFT dimensions from supplied module drawing; IMU/magnetometer body envelopes nominal",
    "board": [100, 100, 60, 40],
    "mounting_holes": [[103, 103], [157, 103], [103, 137], [157, 137]],
    "tft_holes": [[150.67, 110.37], [150.67, 129.63]],
    "modules": [esp, tft, gps, imu, mag, jp, sw1, sw2],
    "board_text": [["WAYPOINT COMPASS", 130, 136.5, 0.9], ["60 x 40 / REV B", 130, 138, 0.8],
                   ["J2 TFT", 149.5, 135, 0.9]],
}
Path(__file__).with_name("module_config.json").write_text(json.dumps(config, indent=2) + "\n")
