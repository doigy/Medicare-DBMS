CREATE TABLE `Cart` (
  `CartID` int NOT NULL,
  `CustomerID` int DEFAULT NULL,
  `ProductID` int NOT NULL,
  `Quantity` int DEFAULT NULL,
  `TotalSalePrice` float DEFAULT NULL,
  PRIMARY KEY (`CartID`,`ProductID`),
  KEY `idx_cart_customer` (`CustomerID`),
  KEY `idx_cart_product` (`ProductID`),
  CONSTRAINT `Cart_ibfk_1` FOREIGN KEY (`CustomerID`) REFERENCES `Customers` (`CustomerID`),
  CONSTRAINT `Cart_ibfk_2` FOREIGN KEY (`ProductID`) REFERENCES `Inventory` (`ProductID`),
  CONSTRAINT `Cart_chk_1` CHECK ((`Quantity` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `CartInventory` (
  `CartID` int DEFAULT NULL,
  `ProductID` int DEFAULT NULL,
  KEY `idx_cartinventory_cart` (`CartID`),
  KEY `idx_cartinventory_product` (`ProductID`),
  CONSTRAINT `CartInventory_ibfk_1` FOREIGN KEY (`CartID`) REFERENCES `Cart` (`CartID`),
  CONSTRAINT `CartInventory_ibfk_2` FOREIGN KEY (`ProductID`) REFERENCES `Inventory` (`ProductID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `Customers` (
  `CustomerID` int NOT NULL,
  `CustomerName` varchar(255) DEFAULT NULL,
  `ContactNumber` varchar(20) DEFAULT NULL,
  `Address` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`CustomerID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `EmployeeInventory` (
  `EmployeeID` int DEFAULT NULL,
  `ProductID` int DEFAULT NULL,
  KEY `idx_employeeinventory_employee` (`EmployeeID`),
  KEY `idx_employeeinventory_product` (`ProductID`),
  CONSTRAINT `EmployeeInventory_ibfk_1` FOREIGN KEY (`EmployeeID`) REFERENCES `Employees` (`EmployeeID`),
  CONSTRAINT `EmployeeInventory_ibfk_2` FOREIGN KEY (`ProductID`) REFERENCES `Inventory` (`ProductID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `Employees` (
  `EmployeeID` int NOT NULL,
  `EmployeeName` varchar(255) DEFAULT NULL,
  `Position` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`EmployeeID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `Inventory` (
  `ProductID` int NOT NULL,
  `ProductName` varchar(255) DEFAULT NULL,
  `Quantity` int DEFAULT NULL,
  `UnitSalePrice` float DEFAULT NULL,
  `ExpiryDate` date DEFAULT NULL,
  `SupplierID` int DEFAULT NULL,
  PRIMARY KEY (`ProductID`),
  KEY `idx_inventory_supplier` (`SupplierID`),
  CONSTRAINT `Inventory_ibfk_1` FOREIGN KEY (`SupplierID`) REFERENCES `Suppliers` (`SupplierID`),
  CONSTRAINT `Inventory_chk_1` CHECK ((`Quantity` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `Suppliers` (
  `SupplierID` int NOT NULL,
  `SupplierName` varchar(255) DEFAULT NULL,
  `ContactNumber` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`SupplierID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;