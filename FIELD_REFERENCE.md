# FileMaker Field Reference

Quick reference for key table field names. Use double quotes for fields with spaces.

## Patients Database (26 tables, main table has 630 columns)

### Patients Table - Key Fields
```
"Patient ID#"        DOUBLE    - Primary key
"Last Name"          VARCHAR
"First Name"         VARCHAR
"Middle Initial"     VARCHAR
"Street Address"     VARCHAR
"City"               VARCHAR
"State"              VARCHAR
"Zip"                VARCHAR
"Home Phone"         VARCHAR
"Work Phone"         VARCHAR
"Birth Date"         DATE
"Social Security #"  VARCHAR
"Date Entered"       DATE
"Exam Date"          DATE
"Recall Date"        DATE
"Type of Insurance"  VARCHAR
```

## Appointments Database (4 tables, 50 columns)

### Appointments Table - Key Fields
```
"patient id#"        DOUBLE    - Links to Patients
"first name"         VARCHAR   - Note: lowercase!
"last name"          VARCHAR   - Note: lowercase!
"dateappt"           DATE      - Appointment date
"timeappt"           TIME      - Appointment time
"doctor"             VARCHAR
"examtype"           VARCHAR
"confirmappt"        VARCHAR
"chartready"         VARCHAR
"dateapptmade"       DATE
"telephone#"         VARCHAR
"emailaddress"       VARCHAR
```

## Transactions Database (47 tables, main has 533 columns)

### Transactions Table - Key Fields
```
"Patient ID#"        DOUBLE    - Links to Patients
"Last Name"          VARCHAR
"First Name"         VARCHAR
"Transaction Date"   DATE
"Transaction #"      DOUBLE
"Exam Proc"          VARCHAR
"CL Fitting Proc"    VARCHAR
"Photos Proc"        VARCHAR
"Office Proc"        VARCHAR
"Fields Proc"        VARCHAR
"SA Proc"            VARCHAR
"Other Proc"         VARCHAR
"Solutions"          VARCHAR
```

## Example Queries

### Search Patients by Name
```sql
SELECT "Patient ID#", "Last Name", "First Name", "Home Phone"
FROM Patients
WHERE "Last Name" LIKE 'Smith%'
```

### Get Today's Appointments
```sql
SELECT "first name", "last name", "timeappt", "doctor", "examtype"
FROM Appointments
WHERE dateappt = '2024-01-30'
ORDER BY timeappt
```

### Get Patient Transactions
```sql
SELECT "Transaction Date", "Transaction #", "Exam Proc"
FROM Transactions
WHERE "Patient ID#" = 12345
```

## Notes

- Field names are CASE SENSITIVE
- Use double quotes for fields with spaces or special characters
- Appointments table uses lowercase field names
- Large tables (Patients, Transactions) - always select specific columns
- FileMaker ODBC doesn't support LIMIT clause - server uses fetchmany()
