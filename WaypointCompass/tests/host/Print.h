#pragma once
#include <cstddef>
#include <cstdint>
class Print { public: virtual ~Print(){} virtual size_t write(uint8_t)=0;
size_t write(const uint8_t* b,size_t n){for(size_t i=0;i<n;i++)write(b[i]);return n;}
size_t print(const char*s){size_t n=0;while(*s){write(*s++);++n;}return n;}
};
