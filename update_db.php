<?php
// Database connection parameters
$servername = "localhost";
$username = "root";
$password = "";
$dbname = "sysarch";

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

echo "Connected to database successfully.<br>";

// SQL query to alter the computer_status table
$sql = "ALTER TABLE computer_status 
        MODIFY COLUMN status ENUM('vacant', 'occupied', 'in_class', 'maintenance') NOT NULL";

// Execute the query
if ($conn->query($sql) === TRUE) {
    echo "Table computer_status updated successfully to include 'maintenance' status.";
} else {
    echo "Error updating table: " . $conn->error;
}

// Close connection
$conn->close();
?> 