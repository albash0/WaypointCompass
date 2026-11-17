#include "../BottleUI.h"
#include <cassert>
#include <string>

void dump(const std::string &directory, const char *name, const bottleui::State &s, uint32_t now = 1250) {
  GFXcanvas16 image(240, 240); assert(image.getBuffer());
  bottleui::draw(image, s, now);
  const std::string path = directory + "/" + name + ".ppm";
  FILE *f = std::fopen(path.c_str(), "wb"); assert(f);
  std::fprintf(f, "P6\n240 240\n255\n");
  for (int y = 0; y < 240; ++y) for (int x = 0; x < 240; ++x) {
    uint16_t c = image.getPixel(x, y);
    if ((x-120)*(x-120)+(y-119)*(y-119)>120*120) c = 0;
    unsigned char pixel[] = {(unsigned char)(((c >> 11) & 31) * 255 / 31), (unsigned char)(((c >> 5) & 63) * 255 / 63), (unsigned char)((c & 31) * 255 / 31)};
    std::fwrite(pixel, 1, 3, f);
  }
  std::fclose(f);
}
int main(int argc, char **argv) {
  assert(argc == 2); bottleui::State s;
  s.used=0;s.view=11;s.tracked=4;s.snr=28;s.rx=160;
  dump(argv[1], "gps-search", s);
  s.fix=true;s.target=true;s.headingValid=true;s.magnetic=true;s.tilt=true;s.calibrated=true;
  s.store=10;s.heading=335;s.bearing=15;s.distance=440;s.used=8;
  dump(argv[1], "nearest-store", s);
  s.store=14;s.heading=175;s.bearing=170;s.distance=1250;
  dump(argv[1], "long-store-name", s);
  s.distance=12;dump(argv[1], "found-it", s);
  s.calibrating=true;s.calRemainingMs=6500;dump(argv[1], "calibration", s);
  s.calibrating=false;s.details=true;s.valid=615;s.bad=2;s.quality=1;dump(argv[1], "details", s);
  s.details=false;s.magnetic=false;s.headingValid=false;s.distance=1000;
  dump(argv[1], "no-heading", s);
  s.fix=false;s.lostFix=true;s.headingValid=true;s.magnetic=true;dump(argv[1], "gps-lost", s);
  std::puts("Rendered eight screens using the firmware's actual Adafruit GFX renderer.");
}
