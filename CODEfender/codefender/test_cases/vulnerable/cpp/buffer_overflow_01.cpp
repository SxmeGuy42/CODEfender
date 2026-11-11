/**
 * Testovací soubor: Buffer Overflow v C++
 * Tento kód ÚMYSLNĚ obsahuje bezpečnostní chyby.
 */

#include <iostream>
#include <cstring>
#include <cstdlib>

using namespace std;

// NEBEZPEČNÉ: Buffer overflow přes strcpy
void copyUsername(char* input) {
    char username[20];
    // BUFFER OVERFLOW - žádná kontrola délky
    strcpy(username, input);
    cout << "Username: " << username << endl;
}

// NEBEZPEČNÉ: gets() je inherentně nebezpečné
void readUserInput() {
    char buffer[100];
    cout << "Enter your message: ";
    // KRITICKÁ CHYBA - gets() je deprecated kvůli buffer overflow
    gets(buffer);
    cout << "You entered: " << buffer << endl;
}

// NEBEZPEČNÉ: sprintf bez kontroly velikosti
void formatMessage(char* name, int age) {
    char message[50];
    // BUFFER OVERFLOW riziko pokud name je dlouhé
    sprintf(message, "Hello %s, you are %d years old", name, age);
    cout << message << endl;
}

// NEBEZPEČNÉ: Use-after-free
void useAfterFree() {
    int* ptr = new int(42);
    delete ptr;
    
    // USE-AFTER-FREE - použití pointeru po delete
    cout << "Value: " << *ptr << endl;
}

// NEBEZPEČNÉ: Neinicializovaná proměnná
void uninitializedVariable() {
    int value;
    // Použití neinicializované proměnné
    if (value > 10) {
        cout << "Value is greater than 10" << endl;
    }
}

// NEBEZPEČNÉ: Integer overflow
void allocateMemory(unsigned int size) {
    // Žádná kontrola na overflow
    unsigned int totalSize = size * sizeof(int);
    int* array = (int*)malloc(totalSize);
    
    // Pokud size je moc velké, totalSize může být malé kvůli overflow
    for (unsigned int i = 0; i < size; i++) {
        array[i] = i;
    }
    
    free(array);
}

// NEBEZPEČNÉ: Format string vulnerability
void printError(char* errorMsg) {
    // FORMAT STRING vulnerability
    printf(errorMsg);  // Mělo by být printf("%s", errorMsg);
}

// NEBEZPEČNÉ: Command injection
void executeCommand(char* filename) {
    char command[256];
    // COMMAND INJECTION - nekontrolovaný vstup do system()
    sprintf(command, "cat %s", filename);
    system(command);
}

int main(int argc, char* argv[]) {
    if (argc > 1) {
        copyUsername(argv[1]);
    }
    
    return 0;
}
