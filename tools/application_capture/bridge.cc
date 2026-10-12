#include "application_input.h"
#include <cstring>
#include <string>
#define NOMINMAX
#include <Windows.h>
#include <TlHelp32.h>
using namespace audio_bridge::audio;
extern "C" {
__declspec(dllexport) unsigned app_resolve(const char* identity) {
  HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
  if(snapshot == INVALID_HANDLE_VALUE) return 0;
  PROCESSENTRY32W entry{}; entry.dwSize=sizeof(entry);
  unsigned found=0;
  if(Process32FirstW(snapshot,&entry)) do {
    HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,entry.th32ProcessID);
    if(!process) continue;
    wchar_t path[32768]; DWORD size=32768;
    if(QueryFullProcessImageNameW(process,0,path,&size)) {
      int n=WideCharToMultiByte(CP_UTF8,0,path,size,nullptr,0,nullptr,nullptr);
      std::string utf8(n,0); WideCharToMultiByte(CP_UTF8,0,path,size,utf8.data(),n,nullptr,nullptr);
      if(_stricmp(utf8.c_str(),identity)==0) found=entry.th32ProcessID;
    }
    CloseHandle(process);
    if(found) break;
  } while(Process32NextW(snapshot,&entry));
  CloseHandle(snapshot); return found;
}
__declspec(dllexport) int app_list(char* buffer, int capacity) {
  auto snapshot = EnumerateApplicationInputs(CurrentApplicationInputExclusions());
  std::string result;
  for (auto& app : snapshot.applications)
    result += std::to_string(app.process_id) + "\t" + app.identity + "\t" + app.display_name + "\n";
  if (capacity <= static_cast<int>(result.size())) return -1;
  std::memcpy(buffer, result.c_str(), result.size()+1);
  return snapshot.error.empty() ? static_cast<int>(snapshot.applications.size()) : -2;
}
__declspec(dllexport) void* app_create() { return new ApplicationInput(); }
__declspec(dllexport) int app_start(void* p, unsigned pid, double rate) {
  return static_cast<ApplicationInput*>(p)->Start(pid, rate);
}
__declspec(dllexport) int app_read(void* p, float* left, float* right, int count) {
  return static_cast<int>(static_cast<ApplicationInput*>(p)->Read(left,right,count));
}
__declspec(dllexport) void app_error(void* p, char* buffer, int capacity) {
  auto text = static_cast<ApplicationInput*>(p)->GetLastError();
  if (capacity > 0) { auto n=std::min(text.size(),static_cast<size_t>(capacity-1)); std::memcpy(buffer,text.data(),n); buffer[n]=0; }
}
__declspec(dllexport) void app_destroy(void* p) { delete static_cast<ApplicationInput*>(p); }
}
