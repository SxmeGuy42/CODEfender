-- Testovací soubor: Bezpečné SQL praktiky
-- Tento soubor by NEMĚL vyvolat bezpečnostní varování

-- SPRÁVNĚ: Stored procedura s parametry (ochrana proti SQL injection)
CREATE PROCEDURE GetUserByName
    @userName NVARCHAR(100)
AS
BEGIN
    -- BEZPEČNÉ: Použití parametru přímo v dotazu
    SELECT id, username, email, created_at
    FROM Users
    WHERE Username = @userName;
END;
GO

-- SPRÁVNĚ: Použití sp_executesql s parametry
CREATE PROCEDURE SearchProducts
    @searchTerm NVARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(500);
    DECLARE @params NVARCHAR(100);
    
    -- BEZPEČNÉ: Parametrizovaný dynamic SQL
    SET @sql = N'SELECT * FROM Products WHERE Name LIKE @search';
    SET @params = N'@search NVARCHAR(100)';
    
    EXEC sp_executesql @sql, @params, @search = @searchTerm;
END;
GO

-- SPRÁVNĚ: Least privilege - minimální nutná oprávnění
-- Aplikační účet pouze s SELECT, INSERT, UPDATE právy
GRANT SELECT ON dbo.Users TO [AppUser];
GRANT SELECT ON dbo.Products TO [AppUser];
GRANT INSERT ON dbo.Orders TO [AppUser];
GRANT UPDATE ON dbo.Orders TO [AppUser];
-- SPRÁVNĚ: Žádná DROP, CREATE, ALTER práva

-- SPRÁVNĚ: Uložení hesel jako hash
CREATE TABLE Users (
    UserId INT PRIMARY KEY IDENTITY(1,1),
    Username NVARCHAR(100) UNIQUE NOT NULL,
    PasswordHash NVARCHAR(255) NOT NULL,  -- Hash místo plain text
    Email NVARCHAR(100) NOT NULL,
    CreatedAt DATETIME DEFAULT GETDATE()
);

-- SPRÁVNĚ: Šifrování citlivých dat
CREATE TABLE CreditCards (
    CardId INT PRIMARY KEY IDENTITY(1,1),
    UserId INT NOT NULL,
    CardNumberEncrypted VARBINARY(256) NOT NULL,  -- Šifrované číslo
    CVVEncrypted VARBINARY(128) NOT NULL,         -- Šifrované CVV
    ExpiryDate DATE NOT NULL,
    CONSTRAINT FK_CreditCards_Users FOREIGN KEY (UserId) REFERENCES Users(UserId)
);

-- SPRÁVNĚ: Funkce pro bezpečné vyhledávání s validací
CREATE FUNCTION dbo.SafeSearchUsers
(
    @searchTerm NVARCHAR(100)
)
RETURNS TABLE
AS
RETURN
(
    -- BEZPEČNÉ: Použití parametru v WHERE klauzuli
    SELECT UserId, Username, Email
    FROM Users
    WHERE Username LIKE '%' + @searchTerm + '%'
       OR Email LIKE '%' + @searchTerm + '%'
);
GO

-- SPRÁVNĚ: Transaction pro atomické operace
CREATE PROCEDURE TransferFunds
    @fromAccountId INT,
    @toAccountId INT,
    @amount DECIMAL(10,2)
AS
BEGIN
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Kontrola zůstatku
        DECLARE @balance DECIMAL(10,2);
        SELECT @balance = Balance FROM Accounts WHERE AccountId = @fromAccountId;
        
        IF @balance < @amount
        BEGIN
            THROW 50001, 'Insufficient funds', 1;
        END
        
        -- Odečtení z prvního účtu
        UPDATE Accounts 
        SET Balance = Balance - @amount 
        WHERE AccountId = @fromAccountId;
        
        -- Přičtení na druhý účet
        UPDATE Accounts 
        SET Balance = Balance + @amount 
        WHERE AccountId = @toAccountId;
        
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

-- SPRÁVNĚ: Audit log pro bezpečnostní události
CREATE TABLE SecurityAuditLog (
    LogId INT PRIMARY KEY IDENTITY(1,1),
    UserId INT,
    Action NVARCHAR(100) NOT NULL,
    Timestamp DATETIME DEFAULT GETDATE(),
    IpAddress NVARCHAR(50),
    Success BIT NOT NULL
);

-- SPRÁVNĚ: Index pro výkon (ne bezpečnostní problém)
CREATE NONCLUSTERED INDEX IX_Users_Username 
ON Users(Username);

-- SPRÁVNĚ: Constraints pro data integrity
ALTER TABLE Users
ADD CONSTRAINT CHK_Username_Length CHECK (LEN(Username) >= 3);

ALTER TABLE Users
ADD CONSTRAINT CHK_Email_Format CHECK (Email LIKE '%@%.%');

-- SPRÁVNĚ: Disable xp_cmdshell (bezpečnostní best practice)
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 0;
RECONFIGURE;
GO
