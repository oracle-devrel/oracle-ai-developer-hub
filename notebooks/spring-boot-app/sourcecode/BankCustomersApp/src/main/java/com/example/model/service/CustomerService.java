package com.example.model.service;

import java.util.List;

import com.example.model.entity.Customer;
  
public interface CustomerService {

    List<Customer> getAllCustomers();

    Customer saveCustomer(Customer customer);
	
	Customer getCustomerById(Long id);
	
	Customer updateCustomer(Customer customer);
	
	void deleteCustomerById(Long id);
}
