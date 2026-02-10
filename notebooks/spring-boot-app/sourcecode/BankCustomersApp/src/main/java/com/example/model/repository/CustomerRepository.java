package com.example.model.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.example.model.entity.Customer;
 
/* 
The repository is responsible for providing data access operations on the entity, 
such as saving, updating, retrieving, and deleting data.
It abstracts the database operations and provides a simplified interface for interacting with the data layer

JpaRepository is a core interface within Spring Data Java Persistence API, designed to simplify data access 
and persistence operations in Java applications using the Java Persistence API (JPA). 
It acts as a powerful abstraction layer, significantly reducing the amount of boilerplate code 
required for common database interactions.
*/


public interface CustomerRepository extends JpaRepository<Customer, Long> {
    
}
