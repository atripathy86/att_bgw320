CREATE DATABASE IF NOT EXISTS device_tracker;
USE device_tracker;

CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mac_address VARCHAR(17),
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    device_type VARCHAR(50),
    first_seen DATETIME,
    last_seen DATETIME,
    UNIQUE KEY unique_device (hostname, ip_address)
);
