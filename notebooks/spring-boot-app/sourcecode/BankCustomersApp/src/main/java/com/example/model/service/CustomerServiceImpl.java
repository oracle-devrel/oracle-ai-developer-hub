package com.example.model.service;

import java.util.List;

import org.springframework.stereotype.Service;

import com.example.model.entity.Customer;
import com.example.model.repository.CustomerRepository; 

/*
The service implementation class implements the Bank Customer interface (CustomerRepository)
and provides the actual implementation of the business logic
*/

@Service
public class CustomerServiceImpl implements CustomerService { 
     
    private CustomerRepository customerRepository;
  
    public CustomerServiceImpl(CustomerRepository customerRepository) {
        super();
        this.customerRepository = customerRepository;
    }
 
    @Override
    public List<Customer> getAllCustomers() {
        return customerRepository.findAll();
    }

    @Override
    public Customer saveCustomer(Customer customer) {
        return customerRepository.save(customer);   
    }
    @Override
    public Customer getCustomerById(Long id) {
        return customerRepository.findById(id).get();   
    }

    @Override
    public Customer updateCustomer(Customer customer) {
        return customerRepository.save(customer);       
    }

    @Override
    public void deleteCustomerById(Long id) {
        customerRepository.deleteById(id);  
    }
 
}
 