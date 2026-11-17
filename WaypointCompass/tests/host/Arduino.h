#pragma once
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <string>
#include <initializer_list>
#define PROGMEM
#define INPUT_PULLUP 2
#define LOW 0
#define HIGH 1
class __FlashStringHelper;
class String: public std::string { public: using std::string::string; };
inline void yield() {}
static uint32_t clockNow=0;
inline uint32_t millis(){return clockNow;}
inline uint32_t micros(){return clockNow*1000;}
inline void delay(int n){clockNow+=n;}
static int pinLevels[49];
inline void pinMode(int pin,int){pinLevels[pin]=1;}
inline int digitalRead(int pin){return pinLevels[pin];}
struct SerialType { void begin(int){} void println(const char*){} template<class... T> void printf(const char*,T...){} };
static SerialType Serial;
inline float radians(float degrees){return degrees*0.017453292519943295f;}
