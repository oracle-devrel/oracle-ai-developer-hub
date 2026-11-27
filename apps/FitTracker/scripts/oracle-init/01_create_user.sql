-- Runs on every start of the Oracle container (mounted at /opt/oracle/scripts/startup).
-- Creates the application user in the pluggable database if it does not exist yet.
ALTER SESSION SET CONTAINER = FREEPDB1;

DECLARE
    user_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM dba_users WHERE username = 'FITTRACK';
    IF user_count = 0 THEN
        EXECUTE IMMEDIATE 'CREATE USER fittrack IDENTIFIED BY "FitTrack2026!" QUOTA UNLIMITED ON USERS';
        EXECUTE IMMEDIATE 'GRANT DB_DEVELOPER_ROLE TO fittrack';
    END IF;
END;
/
