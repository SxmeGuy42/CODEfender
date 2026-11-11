/**
 * Testovací soubor: Bezpečné string operace v C++
 * Tento kód by NEMĚL vyvolat bezpečnostní varování.
 */

#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <cstring>
#include <algorithm>

using namespace std;

// SPRÁVNĚ: Použití std::string místo char array
void copyUsername(const string& input) {
    string username = input;
    cout << "Username: " << username << endl;
}

// SPRÁVNĚ: Použití std::getline místo gets()
void readUserInput() {
    string buffer;
    cout << "Enter your message: ";
    
    // BEZPEČNÉ: std::getline má bounds checking
    getline(cin, buffer);
    cout << "You entered: " << buffer << endl;
}

// SPRÁVNĚ: snprintf s bounds checking
void formatMessage(const char* name, int age) {
    char message[100];
    
    // BEZPEČNÉ: snprintf omezuje velikost výstupu
    snprintf(message, sizeof(message), 
             "Hello %s, you are %d years old", name, age);
    
    cout << message << endl;
}

// SPRÁVNĚ: Použití smart pointerů
void useSmartPointers() {
    // BEZPEČNÉ: unique_ptr automaticky uvolní paměť
    unique_ptr<int> ptr = make_unique<int>(42);
    
    cout << "Value: " << *ptr << endl;
    
    // Automatické uvolnění při výstupu z scope
}

// SPRÁVNĚ: Inicializace proměnných
void initializeVariables() {
    // SPRÁVNĚ: Inicializace při deklaraci
    int value = 0;
    
    if (value > 10) {
        cout << "Value is greater than 10" << endl;
    } else {
        cout << "Value is: " << value << endl;
    }
}

// SPRÁVNĚ: Kontrola integer overflow
bool safeAllocateMemory(size_t count) {
    // SPRÁVNĚ: Kontrola na overflow před alokací
    const size_t MAX_SIZE = SIZE_MAX / sizeof(int);
    
    if (count > MAX_SIZE) {
        cerr << "Error: Size too large, would cause overflow" << endl;
        return false;
    }
    
    size_t totalSize = count * sizeof(int);
    
    // BEZPEČNÉ: Použití vector místo malloc
    vector<int> array(count);
    
    for (size_t i = 0; i < count; i++) {
        array[i] = static_cast<int>(i);
    }
    
    return true;
}

// SPRÁVNĚ: Bezpečné format string
void printError(const string& errorMsg) {
    // BEZPEČNÉ: String je předán jako parametr, ne jako format
    printf("%s\n", errorMsg.c_str());
}

// SPRÁVNĚ: Bezpečné kopírování stringů
void safeCopyString(const char* source) {
    if (!source) {
        cerr << "Error: Null pointer" << endl;
        return;
    }
    
    size_t len = strlen(source);
    const size_t MAX_LEN = 1024;
    
    if (len >= MAX_LEN) {
        cerr << "Error: String too long" << endl;
        return;
    }
    
    char destination[MAX_LEN];
    
    // BEZPEČNÉ: strncpy s explicitní velikostí
    strncpy(destination, source, MAX_LEN - 1);
    destination[MAX_LEN - 1] = '\0'; // Zajištění null-termination
    
    cout << "Copied: " << destination << endl;
}

// SPRÁVNĚ: RAII pattern pro resource management
class FileHandler {
private:
    FILE* file;
    
public:
    FileHandler(const char* filename) {
        file = fopen(filename, "r");
        if (!file) {
            throw runtime_error("Failed to open file");
        }
    }
    
    // SPRÁVNĚ: Destruktor automaticky uzavře soubor
    ~FileHandler() {
        if (file) {
            fclose(file);
        }
    }
    
    // Prevence kopírování
    FileHandler(const FileHandler&) = delete;
    FileHandler& operator=(const FileHandler&) = delete;
};

// SPRÁVNĚ: Bounds checking při přístupu k poli
void safeArrayAccess(const vector<int>& data, size_t index) {
    // BEZPEČNÉ: at() provádí bounds checking
    try {
        int value = data.at(index);
        cout << "Value at " << index << ": " << value << endl;
    } catch (const out_of_range& e) {
        cerr << "Error: Index out of range" << endl;
    }
}

int main(int argc, char* argv[]) {
    if (argc > 1) {
        // BEZPEČNÉ: Použití std::string
        string arg(argv[1]);
        copyUsername(arg);
    }
    
    useSmartPointers();
    initializeVariables();
    safeAllocateMemory(100);
    
    return 0;
}
