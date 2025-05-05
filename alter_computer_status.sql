-- Alter the computer_status table to modify the status enum to include 'maintenance'
ALTER TABLE computer_status 
MODIFY COLUMN status ENUM('vacant', 'occupied', 'in_class', 'maintenance') NOT NULL; 