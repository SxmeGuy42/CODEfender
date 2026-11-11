-- Testovací soubor: SQL Injection příklady
-- Tento soubor obsahuje NEBEZPEČNÉ SQL patterny pro testování

-- NEBEZPEČNÝ PATTERN 1: Dynamic SQL bez parametrizace
DECLARE @username NVARCHAR(100) = 'admin';
DECLARE @sql NVARCHAR(500);

-- SQL INJECTION zranitelnost - string concatenation
SET @sql = 'SELECT * FROM Users WHERE Username = ''' + @username + '''';
EXEC sp_executesql @sql;

-- NEBEZPEČNÝ PATTERN 2: Stored procedura s EXEC
CREATE PROCEDURE GetUserByName
    @userName NVARCHAR(100)
AS
BEGIN
    DECLARE @query NVARCHAR(500);
    -- SQL INJECTION přes EXEC
    SET @query = 'SELECT * FROM Users WHERE Username = ''' + @userName + '''';
    EXEC(@query);
END;

-- NEBEZPEČNÝ PATTERN 3: Chybějící input validace
CREATE PROCEDURE SearchProducts
    @searchTerm NVARCHAR(100)
AS
BEGIN
    -- Žádná sanitizace vstupu
    DECLARE @sql NVARCHAR(500);
    SET @sql = 'SELECT * FROM Products WHERE Name LIKE ''%' + @searchTerm + '%''';
    EXEC sp_executesql @sql;
END;

-- NEBEZPEČNÝ PATTERN 4: Nadměrná oprávnění
-- Aplikační účet s admin právy
GRANT ALL PRIVILEGES ON DATABASE::MyDatabase TO [AppUser];
GRANT CREATE TABLE TO [AppUser];
GRANT DROP TABLE TO [AppUser];
GRANT ALTER TO [AppUser];

-- NEBEZPEČNÝ PATTERN 5: Uložené heslo v plain text
CREATE TABLE Users (
    UserId INT PRIMARY KEY,
    Username NVARCHAR(100),
    Password NVARCHAR(100),  -- Heslo v plain text!
    Email NVARCHAR(100)
);

-- NEBEZPEČNÝ PATTERN 6: Chybějící šifrování citlivých dat
CREATE TABLE CreditCards (
    CardId INT PRIMARY KEY,
    CardNumber NVARCHAR(16),  -- Nešifrované číslo karty
    CVV NVARCHAR(3),          -- Nešifrované CVV
    ExpiryDate DATE
);

-- NEBEZPEČNÉ: xp_cmdshell enabled
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1;
RECONFIGURE;

-- Command injection možnost přes xp_cmdshell
DECLARE @cmd NVARCHAR(100) = 'dir C:\';
EXEC xp_cmdshell @cmd;
